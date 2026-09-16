options(stringsAsFactors = FALSE)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) {
  stop("Usage: extract_private_beta_completed_source_points.R <player_stats_seasonal.RData> <output.csv>")
}

stats_path <- args[[1]]
out_path <- args[[2]]
if (!file.exists(stats_path)) {
  stop("Completed-source stats file does not exist: ", stats_path)
}

pick_col <- function(df, candidates, required = TRUE) {
  hit <- candidates[candidates %in% names(df)]
  if (length(hit)) return(hit[[1]])
  if (required) {
    stop(
      "Missing expected column. Tried: ", paste(candidates, collapse = ", "),
      "; available: ", paste(names(df), collapse = ", ")
    )
  }
  NULL
}

stats_env <- new.env(parent = emptyenv())
loaded <- load(stats_path, envir = stats_env)
if (!("player_stats_seasonal" %in% loaded)) {
  stop(
    "Historical stats file missing player_stats_seasonal; loaded: ",
    paste(loaded, collapse = ", ")
  )
}
stats <- as.data.frame(stats_env$player_stats_seasonal)

stats_id <- pick_col(stats, c("player_id", "gsis_id"))
stats_season <- pick_col(stats, c("season", "year"))
stats_position <- pick_col(stats, c("position_group", "position", "pos"))
stats_points <- pick_col(
  stats,
  c("fantasyPoints", "fantasy_points", "fantasy_points_ppr", "fantasyPoints_ppr")
)

out <- data.frame(
  player_id = as.character(stats[[stats_id]]),
  season = suppressWarnings(as.integer(stats[[stats_season]])),
  position = as.character(stats[[stats_position]]),
  fantasy_points = suppressWarnings(as.numeric(stats[[stats_points]])),
  stringsAsFactors = FALSE
)
out <- out[
  !is.na(out$player_id) & nzchar(trimws(out$player_id)) &
    out$position %in% c("QB", "RB", "WR", "TE") &
    !is.na(out$season) & !is.na(out$fantasy_points),
  , drop = FALSE
]

key <- paste(out$player_id, out$season, sep = "|")
if (anyDuplicated(key)) {
  dupes <- unique(key[duplicated(key)])
  stop("Duplicate completed-source player-season rows found: ", paste(head(dupes, 10), collapse = ", "))
}
if (!any(out$season == 2025L)) {
  stop("Frozen research-coordinate source does not contain completed 2025 player-season rows")
}

out <- out[order(out$season, out$position, out$player_id), , drop = FALSE]
dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
write.csv(out, out_path, row.names = FALSE, na = "")

cat("Frozen-coordinate source rows:", nrow(out), "\n")
cat("Frozen-coordinate seasons:", min(out$season), "through", max(out$season), "\n")
cat("Frozen-coordinate 2025 rows:", sum(out$season == 2025L), "\n")
cat("Frozen-coordinate positions:", paste(sort(unique(out$position)), collapse = ", "), "\n")
