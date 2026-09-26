options(stringsAsFactors = FALSE, timeout = 180)

out_dir <- "artifacts/research/intrinsic_comprehensive_y4_y8_20260926"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
cache_dir <- file.path(out_dir, "cache")
dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)

stats_url <- "https://raw.githubusercontent.com/isaactpetersen/Fantasy-Football-Analytics-Textbook/main/data/player_stats_seasonal.RData"
players_url <- "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"

stats_path <- file.path(cache_dir, "player_stats_seasonal.RData")
players_path <- file.path(cache_dir, "players.csv")
download.file(stats_url, stats_path, mode = "wb", quiet = FALSE)
download.file(players_url, players_path, mode = "wb", quiet = FALSE)

env <- new.env(parent = emptyenv())
loaded <- load(stats_path, envir = env)
if (!("player_stats_seasonal" %in% loaded)) stop("missing player_stats_seasonal")
stats <- as.data.frame(env$player_stats_seasonal)
players <- read.csv(players_path, stringsAsFactors = FALSE, na.strings = c("", "NA"))

write.csv(data.frame(column=names(stats), stringsAsFactors=FALSE),
          file.path(out_dir,"STATS_SCHEMA.csv"),row.names=FALSE)
write.csv(data.frame(column=names(players), stringsAsFactors=FALSE),
          file.path(out_dir,"PLAYERS_SCHEMA.csv"),row.names=FALSE)

norm_name <- function(x) tolower(gsub("[^a-z0-9]+","_",x))
stats_norm <- setNames(names(stats), norm_name(names(stats)))
players_norm <- setNames(names(players), norm_name(names(players)))

find_first <- function(norm_map, candidates) {
  for (cand in candidates) if (cand %in% names(norm_map)) return(unname(norm_map[[cand]]))
  NA_character_
}

sid <- find_first(stats_norm,c("player_id","gsis_id"))
sseason <- find_first(stats_norm,c("season","year"))
spos <- find_first(stats_norm,c("position_group","position","pos"))
if (any(is.na(c(sid,sseason,spos)))) stop("missing identity columns")

s <- stats
s$.__pid <- as.character(s[[sid]])
s$.__season <- suppressWarnings(as.integer(s[[sseason]]))
s$.__pos <- as.character(s[[spos]])
s <- s[!is.na(s$.__pid) & nzchar(s$.__pid) & s$.__pos %in% c("QB","RB","WR","TE") & !is.na(s$.__season),,drop=FALSE]

candidate_groups <- list(
  fantasy_outcome=c("fantasy_points","fantasypoints","fantasy_points_ppr","fantasypoints_ppr"),
  availability=c("games","games_played","gp","starts","games_started"),
  passing_usage=c("attempts","passing_attempts","pass_attempts","completions","passing_completions"),
  passing_efficiency=c("passing_yards","pass_yards","passing_tds","passing_touchdowns","interceptions","passing_interceptions","sacks_suffered"),
  rushing_usage=c("carries","rushing_attempts","rush_attempts"),
  rushing_efficiency=c("rushing_yards","rush_yards","rushing_tds","rushing_touchdowns"),
  receiving_usage=c("targets","receptions"),
  receiving_efficiency=c("receiving_yards","rec_yards","receiving_tds","receiving_touchdowns","receiving_air_yards","air_yards"),
  fumbles=c("fumbles","fumbles_lost"),
  team_context=c("team","recent_team","team_abbr"),
  snap_context=c("offense_snaps","snap_counts","snap_count","snap_pct","offense_snap_pct")
)

rows <- list()
for (group in names(candidate_groups)) {
  for (cand in candidate_groups[[group]]) {
    actual <- if (cand %in% names(stats_norm)) unname(stats_norm[[cand]]) else NA_character_
    if (is.na(actual)) {
      rows[[length(rows)+1]] <- data.frame(
        source="player_stats_seasonal",group=group,candidate=cand,column="",
        available=FALSE,min_season=NA,max_season=NA,nonmissing_rows=0,
        qb_coverage=NA,rb_coverage=NA,wr_coverage=NA,te_coverage=NA
      )
    } else {
      v <- s[[actual]]
      ok <- !is.na(v)
      cov <- sapply(c("QB","RB","WR","TE"), function(p) {
        z <- s$.__pos==p
        if (!sum(z)) return(NA_real_)
        mean(ok[z])
      })
      rows[[length(rows)+1]] <- data.frame(
        source="player_stats_seasonal",group=group,candidate=cand,column=actual,
        available=TRUE,
        min_season=if(any(ok)) min(s$.__season[ok],na.rm=TRUE) else NA,
        max_season=if(any(ok)) max(s$.__season[ok],na.rm=TRUE) else NA,
        nonmissing_rows=sum(ok),
        qb_coverage=cov[["QB"]],rb_coverage=cov[["RB"]],
        wr_coverage=cov[["WR"]],te_coverage=cov[["TE"]]
      )
    }
  }
}

player_candidates <- list(
  identity=c("gsis_id","player_id","display_name","full_name","first_name","last_name"),
  birth_entry=c("birth_date","birthdate","rookie_season","entry_year","draft_year"),
  draft_pedigree=c("draft_year","draft_round","draft_number","draft_pick","draft_club"),
  physical=c("height","weight"),
  school=c("college","college_name","conference"),
  position=c("position","position_group")
)
for (group in names(player_candidates)) {
  for (cand in player_candidates[[group]]) {
    actual <- if (cand %in% names(players_norm)) unname(players_norm[[cand]]) else NA_character_
    if (is.na(actual)) {
      rows[[length(rows)+1]] <- data.frame(
        source="players",group=group,candidate=cand,column="",
        available=FALSE,min_season=NA,max_season=NA,nonmissing_rows=0,
        qb_coverage=NA,rb_coverage=NA,wr_coverage=NA,te_coverage=NA
      )
    } else {
      v <- players[[actual]]
      rows[[length(rows)+1]] <- data.frame(
        source="players",group=group,candidate=cand,column=actual,
        available=TRUE,min_season=NA,max_season=NA,nonmissing_rows=sum(!is.na(v)),
        qb_coverage=NA,rb_coverage=NA,wr_coverage=NA,te_coverage=NA
      )
    }
  }
}

inventory <- do.call(rbind,rows)
write.csv(inventory,file.path(out_dir,"FEATURE_AVAILABILITY_MATRIX.csv"),row.names=FALSE)

actual_cols <- unique(inventory$column[inventory$source=="player_stats_seasonal" & inventory$available & nzchar(inventory$column)])
era <- list()
for (col in actual_cols) {
  ok <- !is.na(s[[col]])
  tmp <- data.frame(season=s$.__season,position=s$.__pos,ok=ok)
  tab <- aggregate(ok ~ season + position, data=tmp, FUN=mean)
  tab$column <- col
  era[[length(era)+1]] <- tab[,c("column","season","position","ok")]
  names(era[[length(era)]])[4] <- "coverage"
}
if(length(era)) write.csv(do.call(rbind,era),file.path(out_dir,"FEATURE_ERA_COVERAGE.csv"),row.names=FALSE)

lines <- c(
  "# Comprehensive Y4-Y8 PIT Evidence Inventory",
  "",
  "This is a schema/coverage inventory only. No model selection and no current-player outcome inspection occur in this pass.",
  "",
  "## Governed historical source classes",
  "",
  "- player_stats_seasonal.RData: historical player-season football outcomes/usage used by existing governed career research.",
  "- nflverse players.csv: identity, birth/entry, draft/pedigree, physical and school metadata used by existing governed research paths.",
  "- Existing governed Y1-Y3 PIT Forecast artifacts remain a separate feature family and are not reconstructed from future outcomes here.",
  "",
  "## PIT treatment",
  "",
  "- Static metadata is eligible only when it would have been known by the base-season forecast cutoff.",
  "- Seasonal football statistics may only enter as lagged evidence from seasons strictly before the base forecast season.",
  "- Same-season or future team/role outcomes are prohibited.",
  "- Current downstream market/value/owner/team-utility signals are prohibited.",
  "",
  "## Data gaps to keep explicit",
  "",
  "- Historical contract guarantees/years remaining are not assumed available unless a governed point-in-time source is separately proven.",
  "- Injury designation/event history is not assumed available merely because games played can proxy availability.",
  "- Depth-chart/starter labels are not assumed PIT reconstructable unless a governed historical source is proven.",
  "- Combine/athletic testing is not assumed from height/weight; it requires its own governed historical source.",
  "- Team investment beyond draft capital is not inferred from hindsight transactions.",
  "",
  "See FEATURE_AVAILABILITY_MATRIX.csv, FEATURE_ERA_COVERAGE.csv, STATS_SCHEMA.csv, and PLAYERS_SCHEMA.csv."
)
writeLines(lines,file.path(out_dir,"EVIDENCE_INVENTORY.md"))
cat(paste(lines,collapse="\n"),"\n")
print(inventory[inventory$available,])
