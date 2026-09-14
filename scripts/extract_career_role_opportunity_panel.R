options(stringsAsFactors = FALSE, timeout = 180)

out_dir <- "artifacts/forecast-role"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
cache_dir <- file.path(out_dir, "cache")
dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)

stats_url <- "https://raw.githubusercontent.com/isaactpetersen/Fantasy-Football-Analytics-Textbook/main/data/player_stats_seasonal.RData"
stats_path <- file.path(cache_dir, "player_stats_seasonal.RData")
download.file(stats_url, stats_path, mode = "wb", quiet = FALSE)

env <- new.env(parent = emptyenv())
loaded <- load(stats_path, envir = env)
if (!("player_stats_seasonal" %in% loaded)) stop("player_stats_seasonal missing")
stats <- as.data.frame(env$player_stats_seasonal)

pick <- function(candidates, required = TRUE) {
  hit <- candidates[candidates %in% names(stats)]
  if (length(hit)) return(hit[[1]])
  if (required) stop("Missing column; tried: ", paste(candidates, collapse=", "))
  NULL
}

id_col <- pick(c("player_id", "gsis_id"))
season_col <- pick(c("season", "year"))
pos_col <- pick(c("position_group", "position", "pos"))
games_col <- pick(c("games", "games_played"))
pass_att_col <- pick(c("attempts", "passing_attempts", "pass_attempts"), FALSE)
carries_col <- pick(c("carries", "rushing_attempts", "rush_attempts"), FALSE)
targets_col <- pick(c("targets"), FALSE)
target_share_col <- pick(c("target_share"), FALSE)
starts_col <- pick(c("starts", "games_started"), FALSE)

num <- function(col) if (is.null(col)) rep(NA_real_, nrow(stats)) else suppressWarnings(as.numeric(stats[[col]]))
base <- data.frame(
  player_id = as.character(stats[[id_col]]),
  season = as.integer(stats[[season_col]]),
  position = as.character(stats[[pos_col]]),
  games = num(games_col),
  starts = num(starts_col),
  passing_attempts = num(pass_att_col),
  carries = num(carries_col),
  targets = num(targets_col),
  target_share = num(target_share_col),
  stringsAsFactors = FALSE
)
base <- base[!is.na(base$player_id) & nzchar(base$player_id) & base$position %in% c("QB","RB","WR","TE") & !is.na(base$season),]
base$games_safe <- pmax(1, ifelse(is.na(base$games), 0, base$games))
base$opportunities <- NA_real_
base$opportunities[base$position == "QB"] <- ifelse(is.na(base$passing_attempts[base$position == "QB"]), 0, base$passing_attempts[base$position == "QB"])
rb <- base$position == "RB"
base$opportunities[rb] <- ifelse(is.na(base$carries[rb]),0,base$carries[rb]) + ifelse(is.na(base$targets[rb]),0,base$targets[rb])
rec <- base$position %in% c("WR","TE")
base$opportunities[rec] <- ifelse(is.na(base$targets[rec]),0,base$targets[rec])
base$opportunities_per_game <- base$opportunities / base$games_safe
base$role_percentile <- NA_real_
for (key in unique(paste(base$season, base$position, sep="|"))) {
  idx <- which(paste(base$season, base$position, sep="|") == key)
  ok <- idx[!is.na(base$opportunities_per_game[idx])]
  if (length(ok)) {
    rr <- rank(base$opportunities_per_game[ok], ties.method="average")
    base$role_percentile[ok] <- (rr - 0.5) / length(ok)
  }
}

prior <- base[,c("player_id","season","games","starts","opportunities","opportunities_per_game","role_percentile","target_share")]
prior$season <- prior$season + 1L
names(prior)[3:8] <- paste0("prior_", names(prior)[3:8])
keys <- paste(prior$player_id, prior$season, sep="|")
prior <- prior[!duplicated(keys),]
write.csv(prior, file.path(out_dir, "career_role_opportunity_panel.csv"), row.names=FALSE, na="")

coverage <- aggregate(player_id ~ season + position, data=base, FUN=length)
names(coverage)[3] <- "player_seasons"
role_ok <- aggregate(role_percentile ~ season + position, data=base, FUN=function(x) sum(!is.na(x)))
names(role_ok)[3] <- "role_rows"
coverage <- merge(coverage, role_ok, by=c("season","position"), all.x=TRUE)
write.csv(coverage, file.path(out_dir, "career_role_opportunity_coverage.csv"), row.names=FALSE, na="")

cat("Role panel rows:", nrow(prior), "\n")
cat("Seasons:", min(base$season), "through", max(base$season), "\n")
cat("Columns used:", paste(c(games_col, pass_att_col, carries_col, targets_col, target_share_col, starts_col), collapse=", "), "\n")
cat("Non-missing prior role percentile:", sum(!is.na(prior$prior_role_percentile)), "of", nrow(prior), "\n")
