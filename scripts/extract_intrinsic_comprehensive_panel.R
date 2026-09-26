options(stringsAsFactors = FALSE)

args <- commandArgs(trailingOnly = TRUE)
rdata_path <- if (length(args) >= 1) args[[1]] else "artifacts/research/intrinsic_comprehensive_y4_y8_20260926/input/player_stats_seasonal.RData"
out_path <- if (length(args) >= 2) args[[2]] else "artifacts/research/intrinsic_comprehensive_y4_y8_20260926/RAW_PLAYER_SEASONS_RICH.csv"

env <- new.env(parent = emptyenv())
loaded <- load(rdata_path, envir = env)
if (!("player_stats_seasonal" %in% loaded)) stop("missing player_stats_seasonal")
d <- as.data.frame(env$player_stats_seasonal)

needed <- c(
  "player_id","season","player_name","position","position_group","team","games",
  "completions","attempts","passing_yards","passing_tds","passing_interceptions",
  "sacks_suffered","passing_air_yards","passing_yards_after_catch","passing_first_downs",
  "passing_epa","passing_cpoe","pacr",
  "carries","rushing_yards","rushing_tds","rushing_first_downs","rushing_epa",
  "receptions","targets","receiving_yards","receiving_tds","receiving_air_yards",
  "receiving_yards_after_catch","receiving_first_downs","receiving_epa",
  "racr","target_share","air_yards_share","wopr",
  "sack_fumbles","sack_fumbles_lost","rushing_fumbles","rushing_fumbles_lost",
  "receiving_fumbles","receiving_fumbles_lost","fumbles",
  "fantasy_points","fantasy_points_ppr","fantasyPoints",
  "birth_date","height","weight","college_name","college_conference",
  "rookie_season","draft_year","draft_round","draft_pick","draft_team",
  "age","years_of_experience"
)
available <- needed[needed %in% names(d)]
x <- d[, available, drop = FALSE]

if ("season_type" %in% names(d)) {
  keep <- d$season_type == "REG" | is.na(d$season_type)
  x <- x[keep, , drop = FALSE]
}
x$player_id <- as.character(x$player_id)
x$season <- suppressWarnings(as.integer(x$season))
x$position <- as.character(x$position)
x <- x[
  !is.na(x$player_id) & nzchar(trimws(x$player_id)) &
  !is.na(x$season) & x$position %in% c("QB","RB","WR","TE"),
  , drop = FALSE
]
key <- paste(x$player_id,x$season,sep="|")
if (anyDuplicated(key)) {
  stop("duplicate player-season rows after regular-season filter")
}
x <- x[order(x$season,x$position,x$player_id),]
dir.create(dirname(out_path),recursive=TRUE,showWarnings=FALSE)
write.csv(x,out_path,row.names=FALSE)

cat("rows",nrow(x),"\n")
cat("seasons",min(x$season),max(x$season),"\n")
cat("columns",paste(names(x),collapse=","),"\n")
