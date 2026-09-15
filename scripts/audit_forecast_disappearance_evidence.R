options(stringsAsFactors = FALSE, timeout = 180)

out_dir <- "artifacts/forecast-disappearance/evidence-audit"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
cache_dir <- file.path(out_dir, "cache")
dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)

stats_url <- "https://raw.githubusercontent.com/isaactpetersen/Fantasy-Football-Analytics-Textbook/main/data/player_stats_seasonal.RData"
players_url <- "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"
stats_path <- file.path(cache_dir, "player_stats_seasonal.RData")
players_path <- file.path(cache_dir, "players.csv")
download.file(stats_url, stats_path, mode = "wb", quiet = TRUE)
download.file(players_url, players_path, mode = "wb", quiet = TRUE)

env <- new.env(parent = emptyenv())
loaded <- load(stats_path, envir = env)
if (!("player_stats_seasonal" %in% loaded)) stop("missing player_stats_seasonal")
stats <- as.data.frame(env$player_stats_seasonal)
players <- read.csv(players_path, stringsAsFactors = FALSE, na.strings = c("", "NA"))
writeLines(names(stats), file.path(out_dir, "historical_stats_columns.txt"))
writeLines(names(players), file.path(out_dir, "players_columns.txt"))

pick <- function(df, candidates) {
  hit <- candidates[candidates %in% names(df)]
  if (length(hit)) hit[[1]] else NA_character_
}
pos_col <- pick(stats, c("position_group", "position", "pos"))
season_col <- pick(stats, c("season", "year"))
id_col <- pick(stats, c("player_id", "gsis_id"))
if (is.na(pos_col) || is.na(season_col) || is.na(id_col)) stop("required identity columns unavailable")

canonical <- list(
  fantasy_points = c("fantasyPoints", "fantasy_points", "fantasy_points_ppr", "fantasyPoints_ppr"),
  games = c("games", "games_played", "gamesPlayed", "g"),
  starts = c("gamesStarted", "games_started", "starts", "gs"),
  pass_attempts = c("passAttempts", "passing_attempts", "pass_attempts", "attempts", "pass_att"),
  rush_attempts = c("rushingAttempts", "rushing_attempts", "rush_attempts", "carries", "rush_att"),
  targets = c("targets", "receivingTargets", "receiving_targets", "tgt"),
  receptions = c("receptions", "rec"),
  touches = c("touches"),
  snaps = c("snaps", "snap_count", "snapCount", "offensive_snaps"),
  snap_share = c("snap_share", "snap_pct", "snapPercent", "offensive_snap_share"),
  routes = c("routes", "routes_run", "routesRun"),
  route_participation = c("route_participation", "routeParticipation", "route_rate")
)

base_pos <- toupper(trimws(as.character(stats[[pos_col]])))
base_season <- suppressWarnings(as.integer(stats[[season_col]]))
keep_pos <- base_pos %in% c("QB", "RB", "WR", "TE")
rows <- list(); k <- 1
for (nm in names(canonical)) {
  col <- pick(stats, canonical[[nm]])
  if (is.na(col)) {
    rows[[k]] <- data.frame(family = nm, source_column = NA_character_, position = "ALL", earliest_season = NA_integer_, latest_season = NA_integer_, rows = 0L, nonmissing = 0L, coverage = 0, stringsAsFactors = FALSE); k <- k + 1
    next
  }
  vals <- suppressWarnings(as.numeric(stats[[col]]))
  for (p in c("QB", "RB", "WR", "TE", "ALL")) {
    ix <- keep_pos & !is.na(base_season)
    if (p != "ALL") ix <- ix & base_pos == p
    n <- sum(ix); ok <- ix & !is.na(vals)
    seasons_ok <- base_season[ok]
    rows[[k]] <- data.frame(
      family = nm, source_column = col, position = p,
      earliest_season = if (length(seasons_ok)) min(seasons_ok) else NA_integer_,
      latest_season = if (length(seasons_ok)) max(seasons_ok) else NA_integer_,
      rows = n, nonmissing = sum(ok), coverage = if (n) sum(ok)/n else 0,
      stringsAsFactors = FALSE
    ); k <- k + 1
  }
}
coverage <- do.call(rbind, rows)
write.csv(coverage, file.path(out_dir, "candidate_evidence_coverage.csv"), row.names = FALSE, na = "")

pid <- pick(players, c("gsis_id", "player_id")); ppos <- pick(players, c("position", "position_group", "pos"))
draft_fields <- list(draft_year = c("draft_year"), draft_round = c("draft_round", "draft_round_number"), draft_pick = c("draft_pick", "draft_number", "draft_pick_number"), rookie_season = c("rookie_season", "entry_year"))
drows <- list(); j <- 1
for (nm in names(draft_fields)) {
  col <- pick(players, draft_fields[[nm]])
  if (is.na(col)) {
    drows[[j]] <- data.frame(family=nm,source_column=NA_character_,position="ALL",rows=0L,nonmissing=0L,coverage=0,stringsAsFactors=FALSE); j <- j+1; next
  }
  vals <- players[[col]]; pos <- if (!is.na(ppos)) toupper(trimws(as.character(players[[ppos]]))) else rep("", nrow(players))
  for (p in c("QB","RB","WR","TE","ALL")) {
    ix <- if (p=="ALL") rep(TRUE,nrow(players)) else pos==p
    n <- sum(ix); ok <- ix & !is.na(vals) & nzchar(trimws(as.character(vals)))
    drows[[j]] <- data.frame(family=nm,source_column=col,position=p,rows=n,nonmissing=sum(ok),coverage=if(n)sum(ok)/n else 0,stringsAsFactors=FALSE); j <- j+1
  }
}
write.csv(do.call(rbind,drows), file.path(out_dir, "pedigree_evidence_coverage.csv"), row.names = FALSE, na = "")

cat("Historical stats source:", stats_url, "\n")
cat("Rows:", nrow(stats), " columns:", ncol(stats), "\n")
print(coverage)
