options(stringsAsFactors = FALSE, timeout = 240)

out_dir <- "artifacts/research/future-state-phase2"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
cache_dir <- file.path(out_dir, "cache")
dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)

stats_url <- "https://raw.githubusercontent.com/isaactpetersen/Fantasy-Football-Analytics-Textbook/main/data/player_stats_seasonal.RData"
players_url <- "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"
stats_path <- file.path(cache_dir, "player_stats_seasonal.RData")
players_path <- file.path(cache_dir, "players.csv")
download.file(stats_url, stats_path, mode = "wb", quiet = TRUE)
download.file(players_url, players_path, mode = "wb", quiet = TRUE)

stats_env <- new.env(parent = emptyenv())
loaded <- load(stats_path, envir = stats_env)
if (!("player_stats_seasonal" %in% loaded)) stop("missing player_stats_seasonal")
s <- as.data.frame(stats_env$player_stats_seasonal)
p <- read.csv(players_path, stringsAsFactors = FALSE, na.strings = c("", "NA"))

pick_col <- function(df, candidates, required = TRUE) {
  hit <- candidates[candidates %in% names(df)]
  if (length(hit)) return(hit[[1]])
  if (required) stop("Missing expected column. Tried: ", paste(candidates, collapse=", "))
  NULL
}

sid <- pick_col(s, c("player_id", "gsis_id"))
season_col <- pick_col(s, c("season", "year"))
pos_col <- pick_col(s, c("position_group", "position", "pos"))
pts_col <- pick_col(s, c("fantasyPoints", "fantasy_points", "fantasy_points_ppr", "fantasyPoints_ppr"))
games_col <- pick_col(s, c("games"))
attempts_col <- pick_col(s, c("attempts"))
carries_col <- pick_col(s, c("carries"))
targets_col <- pick_col(s, c("targets"))
receptions_col <- pick_col(s, c("receptions"), required=FALSE)

pid <- pick_col(p, c("gsis_id", "player_id"))
birth_col <- pick_col(p, c("birth_date", "birthdate", "date_of_birth"))
entry_col <- pick_col(p, c("rookie_season", "entry_year", "draft_year"), required=FALSE)

x <- data.frame(
  player_id = as.character(s[[sid]]),
  season = as.integer(s[[season_col]]),
  position = toupper(as.character(s[[pos_col]])),
  fantasy_points = suppressWarnings(as.numeric(s[[pts_col]])),
  games = suppressWarnings(as.numeric(s[[games_col]])),
  attempts = suppressWarnings(as.numeric(s[[attempts_col]])),
  carries = suppressWarnings(as.numeric(s[[carries_col]])),
  targets = suppressWarnings(as.numeric(s[[targets_col]])),
  receptions = if (!is.null(receptions_col)) suppressWarnings(as.numeric(s[[receptions_col]])) else NA_real_,
  stringsAsFactors = FALSE
)
x <- x[!is.na(x$player_id) & nzchar(trimws(x$player_id)) & x$position %in% c("QB","RB","WR","TE") & !is.na(x$season) & !is.na(x$fantasy_points), , drop=FALSE]
key <- paste(x$player_id, x$season, sep="|")
if (anyDuplicated(key)) stop("duplicate player-season rows")

ident <- data.frame(
  player_id = as.character(p[[pid]]),
  birth_date = as.Date(p[[birth_col]]),
  entry_season = if (!is.null(entry_col)) suppressWarnings(as.integer(p[[entry_col]])) else NA_integer_,
  stringsAsFactors = FALSE
)
ident <- ident[!is.na(ident$player_id) & nzchar(trimws(ident$player_id)), , drop=FALSE]
ident <- ident[!duplicated(ident$player_id), , drop=FALSE]
x <- merge(x, ident, by="player_id", all.x=TRUE)
first_obs <- aggregate(season ~ player_id, data=x, FUN=min)
names(first_obs)[2] <- "first_observed_season"
x <- merge(x, first_obs, by="player_id", all.x=TRUE)
x$entry_season_used <- ifelse(!is.na(x$entry_season), x$entry_season, x$first_observed_season)
x$experience_years <- pmax(0L, x$season - x$entry_season_used)
season_date <- as.Date(sprintf("%d-09-01", x$season))
x$age_years <- as.numeric(season_date - x$birth_date) / 365.2425
x$age_floor <- ifelse(is.na(x$age_years), NA_integer_, floor(x$age_years))

x$opportunity <- ifelse(x$position=="QB", x$attempts, ifelse(x$position=="RB", x$carries + x$targets, x$targets))
x$opportunity_per_game <- ifelse(!is.na(x$games) & x$games > 0, x$opportunity / x$games, 0)
x$role_band <- NA_character_
for (k in unique(paste(x$season,x$position,sep="|"))) {
  ix <- paste(x$season,x$position,sep="|") == k
  med <- median(x$opportunity_per_game[ix], na.rm=TRUE)
  x$role_band[ix] <- ifelse(x$opportunity_per_game[ix] < med, "weak", "established")
}

last_obs <- aggregate(season ~ player_id, data=x, FUN=max)
names(last_obs)[2] <- "last_observed_season"
x <- merge(x,last_obs,by="player_id",all.x=TRUE)
x <- x[order(x$season,x$position,x$player_id),]
write.csv(x, file.path(out_dir,"phase2_player_season_panel.csv"), row.names=FALSE, na="")
cat("rows",nrow(x),"seasons",min(x$season),max(x$season),"age_known",sum(!is.na(x$age_years)),"\n")
print(table(x$position))
