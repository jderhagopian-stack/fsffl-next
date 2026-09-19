options(stringsAsFactors = FALSE, timeout = 180)

out_dir <- "artifacts/next2-career"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
cache_dir <- file.path(out_dir, "cache")
dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)

stats_url <- "https://raw.githubusercontent.com/isaactpetersen/Fantasy-Football-Analytics-Textbook/main/data/player_stats_seasonal.RData"
players_url <- "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"

stats_path <- file.path(cache_dir, "player_stats_seasonal.RData")
players_path <- file.path(cache_dir, "players.csv")
download.file(stats_url, stats_path, mode = "wb", quiet = FALSE)
download.file(players_url, players_path, mode = "wb", quiet = FALSE)

pick_col <- function(df, candidates, required = TRUE) {
  hit <- candidates[candidates %in% names(df)]
  if (length(hit)) return(hit[[1]])
  if (required) stop("Missing expected column. Tried: ", paste(candidates, collapse = ", "), "; available: ", paste(names(df), collapse = ", "))
  NULL
}

stats_env <- new.env(parent = emptyenv())
loaded <- load(stats_path, envir = stats_env)
if (!("player_stats_seasonal" %in% loaded)) {
  stop("Historical stats file missing player_stats_seasonal; loaded: ", paste(loaded, collapse = ", "))
}
stats <- as.data.frame(stats_env$player_stats_seasonal)
players <- read.csv(players_path, stringsAsFactors = FALSE, na.strings = c("", "NA"))

stats_id <- pick_col(stats, c("player_id", "gsis_id"))
stats_season <- pick_col(stats, c("season", "year"))
stats_position <- pick_col(stats, c("position_group", "position", "pos"))
stats_points <- pick_col(stats, c("fantasyPoints", "fantasy_points", "fantasy_points_ppr", "fantasyPoints_ppr"))
players_id <- pick_col(players, c("gsis_id", "player_id"))
birth_col <- pick_col(players, c("birth_date", "birthdate", "date_of_birth"))
entry_col <- pick_col(players, c("rookie_season", "entry_year", "draft_year"), required = FALSE)

base <- data.frame(
  player_id = as.character(stats[[stats_id]]),
  season = as.integer(stats[[stats_season]]),
  position = as.character(stats[[stats_position]]),
  fantasy_points = suppressWarnings(as.numeric(stats[[stats_points]])),
  stringsAsFactors = FALSE
)
base <- base[
  !is.na(base$player_id) & nzchar(trimws(base$player_id)) &
    base$position %in% c("QB", "RB", "WR", "TE") &
    !is.na(base$season) & !is.na(base$fantasy_points),
  , drop = FALSE
]

# This historical object should already be one regular-season row per player-season.
# Fail loudly rather than silently choosing among duplicates.
key <- paste(base$player_id, base$season, sep = "|")
if (anyDuplicated(key)) {
  dupes <- unique(key[duplicated(key)])
  stop("Duplicate historical player-season rows found: ", paste(head(dupes, 10), collapse = ", "))
}

identity <- data.frame(
  player_id = as.character(players[[players_id]]),
  birth_date = as.Date(players[[birth_col]]),
  stringsAsFactors = FALSE
)
if (!is.null(entry_col)) {
  identity$entry_season <- suppressWarnings(as.integer(players[[entry_col]]))
} else {
  identity$entry_season <- NA_integer_
}
identity <- identity[!is.na(identity$player_id) & nzchar(trimws(identity$player_id)), , drop = FALSE]
identity <- identity[!duplicated(identity$player_id), , drop = FALSE]

base <- merge(base, identity, by = "player_id", all.x = TRUE)
first_observed <- aggregate(season ~ player_id, data = base, FUN = min)
names(first_observed)[2] <- "first_observed_season"
base <- merge(base, first_observed, by = "player_id", all.x = TRUE)
base$experience_basis <- ifelse(!is.na(base$entry_season), "player_entry_season", "first_observed_stat_season")
base$entry_season_used <- ifelse(!is.na(base$entry_season), base$entry_season, base$first_observed_season)
base$experience_years <- pmax(0L, base$season - base$entry_season_used)

# Season age is measured at September 1 because this calibration is intended to
# roll preseason/full-season football forecasts into the next season.
season_date <- as.Date(sprintf("%d-09-01", base$season))
base$age_years <- as.numeric(season_date - base$birth_date) / 365.2425

# Prior-production percentile is empirical within each position-season and is
# retained as a continuous feature; later calibration can choose data-supported
# pooling rather than hardcoding a production cutoff here.
base$prior_production_percentile <- NA_real_
groups <- split(seq_len(nrow(base)), paste(base$season, base$position, sep = "|"))
for (idx in groups) {
  n <- length(idx)
  ranks <- rank(base$fantasy_points[idx], ties.method = "average")
  base$prior_production_percentile[idx] <- (ranks - 0.5) / n
}

next_rows <- base[, c("player_id", "season", "fantasy_points")]
next_rows$season <- next_rows$season - 1L
names(next_rows)[names(next_rows) == "fantasy_points"] <- "next_fantasy_points"
panel <- merge(base, next_rows, by = c("player_id", "season"), all.x = TRUE)
max_complete_season <- max(base$season, na.rm = TRUE) - 1L
panel <- panel[panel$season <= max_complete_season, , drop = FALSE]
panel$survived_next_season <- !is.na(panel$next_fantasy_points)
panel$next_fantasy_points[is.na(panel$next_fantasy_points)] <- 0
panel$is_rookie_cohort <- panel$experience_years == 0L
panel$age_year_floor <- ifelse(is.na(panel$age_years), NA_integer_, floor(panel$age_years))

keep <- c(
  "player_id", "season", "position", "fantasy_points", "next_fantasy_points",
  "survived_next_season", "age_years", "age_year_floor", "experience_years",
  "experience_basis", "is_rookie_cohort", "prior_production_percentile"
)
panel <- panel[, keep, drop = FALSE]
panel <- panel[order(panel$season, panel$position, panel$player_id), ]
write.csv(panel, file.path(out_dir, "career_transition_panel.csv"), row.names = FALSE)

coverage <- aggregate(player_id ~ season + position, data = panel, FUN = length)
names(coverage)[3] <- "player_seasons"
write.csv(coverage, file.path(out_dir, "career_transition_coverage.csv"), row.names = FALSE)

cat("Career transition rows:", nrow(panel), "\n")
cat("Seasons:", min(panel$season), "through", max(panel$season), "\n")
cat("Positions:", paste(sort(unique(panel$position)), collapse = ", "), "\n")
cat("Rows with known age:", sum(!is.na(panel$age_years)), "of", nrow(panel), "\n")
cat("Rows using explicit player entry season:", sum(panel$experience_basis == "player_entry_season"), "of", nrow(panel), "\n")
cat("Next-season survival rate:", round(mean(panel$survived_next_season), 4), "\n")
print(tail(coverage, 20))
