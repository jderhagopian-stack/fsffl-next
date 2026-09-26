options(stringsAsFactors = FALSE, timeout = 180)

out_dir <- "artifacts/research/intrinsic_term_structure_20260926"
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
  if (required) stop("Missing expected column. Tried: ", paste(candidates, collapse = ", "))
  NULL
}

env <- new.env(parent = emptyenv())
loaded <- load(stats_path, envir = env)
if (!("player_stats_seasonal" %in% loaded)) stop("missing player_stats_seasonal")
stats <- as.data.frame(env$player_stats_seasonal)
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
  base$position %in% c("QB","RB","WR","TE") &
  !is.na(base$season) & !is.na(base$fantasy_points), , drop = FALSE
]
key <- paste(base$player_id, base$season, sep="|")
if (anyDuplicated(key)) stop("duplicate player-season rows")

identity <- data.frame(
  player_id = as.character(players[[players_id]]),
  birth_date = as.Date(players[[birth_col]]),
  stringsAsFactors = FALSE
)
identity$entry_season <- if (!is.null(entry_col)) suppressWarnings(as.integer(players[[entry_col]])) else NA_integer_
identity <- identity[!is.na(identity$player_id) & nzchar(trimws(identity$player_id)), , drop = FALSE]
identity <- identity[!duplicated(identity$player_id), , drop = FALSE]

base <- merge(base, identity, by="player_id", all.x=TRUE)
first_observed <- aggregate(season ~ player_id, data=base, FUN=min)
names(first_observed)[2] <- "first_observed_season"
base <- merge(base, first_observed, by="player_id", all.x=TRUE)
base$entry_season_used <- ifelse(!is.na(base$entry_season), base$entry_season, base$first_observed_season)
base$experience_years <- pmax(0L, base$season - base$entry_season_used)
season_date <- as.Date(sprintf("%d-09-01", base$season))
base$age_years <- as.numeric(season_date - base$birth_date) / 365.2425
base$prior_production_percentile <- NA_real_
groups <- split(seq_len(nrow(base)), paste(base$season, base$position, sep="|"))
for (idx in groups) {
  n <- length(idx)
  rr <- rank(base$fantasy_points[idx], ties.method="average")
  base$prior_production_percentile[idx] <- (rr - 0.5) / n
}
base <- base[, c("player_id","season","position","fantasy_points","age_years","experience_years","prior_production_percentile")]
base <- base[order(base$season,base$position,base$player_id),]
write.csv(base, file.path(out_dir,"PLAYER_SEASONS.csv"), row.names=FALSE)

cat("rows",nrow(base),"\n")
cat("seasons",min(base$season),max(base$season),"\n")
cat("positions",paste(sort(unique(base$position)),collapse=","),"\n")
