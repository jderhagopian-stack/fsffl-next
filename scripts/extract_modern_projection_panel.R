options(stringsAsFactors = FALSE, timeout = 180)

out_dir <- "artifacts/next2-benchmark"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
cache_dir <- file.path(out_dir, "cache")
dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)

base <- "https://raw.githubusercontent.com/isaactpetersen/Fantasy-Football-Analytics-Textbook/main"
files <- c(
  proj2024 = "data/by_year/players_projectedPoints_seasonal_2024.RData",
  proj2025 = "data/by_year/players_projectedPoints_seasonal_2025.RData",
  stats = "data/player_stats_seasonal.RData",
  ids = "data/nfl_playerIDs.RData"
)

fetch <- function(key, rel) {
  dest <- file.path(cache_dir, basename(rel))
  url <- paste(base, rel, sep = "/")
  message("Downloading ", key, " from ", url)
  download.file(url, dest, mode = "wb", quiet = FALSE)
  dest
}

paths <- mapply(fetch, names(files), files, SIMPLIFY = TRUE)

pick_col <- function(df, candidates, required = TRUE) {
  hit <- candidates[candidates %in% names(df)]
  if (length(hit)) return(hit[[1]])
  if (required) stop("Missing expected column. Tried: ", paste(candidates, collapse = ", "), "; available: ", paste(names(df), collapse = ", "))
  NULL
}

rbind_fill <- function(frames) {
  all_names <- unique(unlist(lapply(frames, names), use.names = FALSE))
  frames <- lapply(frames, function(d) {
    missing <- setdiff(all_names, names(d))
    if (length(missing)) {
      for (nm in missing) d[[nm]] <- NA
    }
    d[, all_names, drop = FALSE]
  })
  out <- do.call(rbind, frames)
  rownames(out) <- NULL
  out
}

load_one_projection_year <- function(path, season) {
  env <- new.env(parent = emptyenv())
  loaded <- load(path, envir = env)
  if (!("players_projectedPoints_seasonal" %in% loaded)) {
    stop("Projection file missing players_projectedPoints_seasonal; loaded: ", paste(loaded, collapse = ", "))
  }
  obj <- env$players_projectedPoints_seasonal
  keep_pos <- intersect(c("QB", "RB", "WR", "TE"), names(obj))
  if (!length(keep_pos)) stop("No QB/RB/WR/TE tables found in projection object")
  rows <- lapply(keep_pos, function(pos) {
    d <- as.data.frame(obj[[pos]])
    d$season <- season
    d$position_fsffl <- pos
    d
  })
  rbind_fill(rows)
}

p24 <- load_one_projection_year(paths[["proj2024"]], 2024L)
p25 <- load_one_projection_year(paths[["proj2025"]], 2025L)
proj <- rbind_fill(list(p24, p25))

# Projection schema used by Fantasy Football Analytics historical objects.
id_col <- pick_col(proj, c("id", "mfl_id", "player_id"))
source_col <- pick_col(proj, c("data_src", "source"))
points_col <- pick_col(proj, c("raw_points", "fantasyPoints", "points"))
player_col <- pick_col(proj, c("player", "name", "player_name"), required = FALSE)
pos_col <- pick_col(proj, c("pos", "position", "position_fsffl"), required = FALSE)

# Load realized season outcomes and player identifier crosswalk.
stats_env <- new.env(parent = emptyenv())
stats_loaded <- load(paths[["stats"]], envir = stats_env)
if (!("player_stats_seasonal" %in% stats_loaded)) {
  stop("player_stats_seasonal.RData missing player_stats_seasonal; loaded: ", paste(stats_loaded, collapse = ", "))
}
stats <- as.data.frame(stats_env$player_stats_seasonal)

ids_env <- new.env(parent = emptyenv())
ids_loaded <- load(paths[["ids"]], envir = ids_env)
if (!("nfl_playerIDs" %in% ids_loaded)) {
  stop("nfl_playerIDs.RData missing nfl_playerIDs; loaded: ", paste(ids_loaded, collapse = ", "))
}
ids <- as.data.frame(ids_env$nfl_playerIDs)

stats_gsis_col <- pick_col(stats, c("player_id", "gsis_id"))
stats_season_col <- pick_col(stats, c("season", "year"))
actual_col <- pick_col(stats, c("fantasyPoints", "fantasy_points", "fantasy_points_ppr", "fantasyPoints_ppr"))
stats_pos_col <- pick_col(stats, c("position_group", "position", "pos"), required = FALSE)
stats_name_col <- pick_col(stats, c("player_display_name", "player_name", "player"), required = FALSE)

ids_gsis_col <- pick_col(ids, c("gsis_id", "player_id"))
ids_mfl_col <- pick_col(ids, c("mfl_id", "id"))

cross <- ids[, c(ids_gsis_col, ids_mfl_col), drop = FALSE]
names(cross) <- c("gsis_id_key", "mfl_id_key")
cross <- cross[!is.na(cross$gsis_id_key) & !is.na(cross$mfl_id_key), , drop = FALSE]
cross <- cross[!duplicated(cross$gsis_id_key), , drop = FALSE]

actual <- data.frame(
  gsis_id_key = as.character(stats[[stats_gsis_col]]),
  season = as.integer(stats[[stats_season_col]]),
  actual = as.numeric(stats[[actual_col]]),
  stringsAsFactors = FALSE
)
actual$position_actual <- if (!is.null(stats_pos_col)) as.character(stats[[stats_pos_col]]) else NA_character_
actual$player_actual <- if (!is.null(stats_name_col)) as.character(stats[[stats_name_col]]) else NA_character_
actual <- actual[actual$season %in% c(2024L, 2025L), , drop = FALSE]
actual <- merge(actual, cross, by = "gsis_id_key", all.x = TRUE)

projection <- data.frame(
  season = as.integer(proj$season),
  mfl_id_key = as.character(proj[[id_col]]),
  source = as.character(proj[[source_col]]),
  projected = as.numeric(proj[[points_col]]),
  position = if (!is.null(pos_col)) as.character(proj[[pos_col]]) else as.character(proj$position_fsffl),
  player = if (!is.null(player_col)) as.character(proj[[player_col]]) else NA_character_,
  stringsAsFactors = FALSE
)
projection$position <- ifelse(is.na(projection$position) | projection$position == "", as.character(proj$position_fsffl), projection$position)
projection <- projection[projection$position %in% c("QB", "RB", "WR", "TE") & !is.na(projection$projected), , drop = FALSE]

panel <- merge(projection, actual[, c("season", "mfl_id_key", "actual", "player_actual", "position_actual")], by = c("season", "mfl_id_key"), all.x = TRUE)
panel$player <- ifelse(is.na(panel$player) | panel$player == "", panel$player_actual, panel$player)
panel$position <- ifelse(is.na(panel$position) | panel$position == "", panel$position_actual, panel$position)
panel <- panel[!is.na(panel$actual) & !is.na(panel$projected), c("season", "mfl_id_key", "player", "position", "source", "projected", "actual")]

# Keep one row per source/player/season. Exact duplicates are harmless; conflicting duplicates are surfaced.
key <- paste(panel$season, panel$mfl_id_key, panel$position, panel$source, sep = "|")
dupe_keys <- unique(key[duplicated(key)])
if (length(dupe_keys)) {
  conflicts <- lapply(dupe_keys, function(k) unique(panel$projected[key == k]))
  bad <- dupe_keys[vapply(conflicts, length, integer(1)) > 1L]
  if (length(bad)) stop("Conflicting duplicate projection rows found: ", paste(head(bad, 10), collapse = ", "))
  panel <- panel[!duplicated(key), , drop = FALSE]
}

panel <- panel[order(panel$season, panel$position, panel$source, panel$player), ]
write.csv(panel, file.path(out_dir, "modern_projection_panel.csv"), row.names = FALSE)

coverage <- aggregate(mfl_id_key ~ season + position + source, data = panel, FUN = length)
names(coverage)[names(coverage) == "mfl_id_key"] <- "matched_players"
coverage <- coverage[order(coverage$season, coverage$position, -coverage$matched_players), ]
write.csv(coverage, file.path(out_dir, "source_coverage.csv"), row.names = FALSE)

cat("Projection rows:", nrow(projection), "\n")
cat("Matched benchmark rows:", nrow(panel), "\n")
cat("Sources:", paste(sort(unique(panel$source)), collapse = ", "), "\n")
cat("Seasons:", paste(sort(unique(panel$season)), collapse = ", "), "\n")
cat("Positions:", paste(sort(unique(panel$position)), collapse = ", "), "\n")
print(coverage)
