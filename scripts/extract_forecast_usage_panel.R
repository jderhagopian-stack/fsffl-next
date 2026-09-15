options(stringsAsFactors = FALSE, timeout = 180)
out_dir <- "artifacts/forecast-disappearance/final"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
cache_dir <- file.path(out_dir, "cache")
dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)
url <- "https://raw.githubusercontent.com/isaactpetersen/Fantasy-Football-Analytics-Textbook/main/data/player_stats_seasonal.RData"
path <- file.path(cache_dir, "player_stats_seasonal.RData")
download.file(url, path, mode="wb", quiet=TRUE)
env <- new.env(parent=emptyenv()); loaded <- load(path,envir=env)
if (!("player_stats_seasonal" %in% loaded)) stop("missing player_stats_seasonal")
s <- as.data.frame(env$player_stats_seasonal)
req <- c("player_id","season","position_group","games","attempts","carries","targets")
missing <- req[!req %in% names(s)]
if (length(missing)) stop("missing required usage columns: ",paste(missing,collapse=","))
x <- data.frame(
 player_id=as.character(s$player_id), season=as.integer(s$season), position=toupper(as.character(s$position_group)),
 games=as.numeric(s$games), attempts=as.numeric(s$attempts), carries=as.numeric(s$carries), targets=as.numeric(s$targets), stringsAsFactors=FALSE)
x <- x[x$position %in% c("QB","RB","WR","TE") & !is.na(x$player_id) & nzchar(x$player_id) & !is.na(x$season),]
x$opportunity <- ifelse(x$position=="QB", x$attempts, ifelse(x$position=="RB", x$carries+x$targets, x$targets))
x$opportunity_per_game <- ifelse(!is.na(x$games) & x$games>0, x$opportunity/x$games, 0)
# Contemporaneous within-season/position median uses only information from the same completed source season.
x$role_band <- NA_character_
for (key in unique(paste(x$season,x$position,sep="|"))) {
  ix <- paste(x$season,x$position,sep="|")==key
  med <- median(x$opportunity_per_game[ix],na.rm=TRUE)
  x$role_band[ix] <- ifelse(x$opportunity_per_game[ix] < med,"weak","established")
}
if (anyDuplicated(paste(x$player_id,x$season,sep="|"))) stop("duplicate usage player-season")
write.csv(x,file.path(out_dir,"forecast_usage_panel.csv"),row.names=FALSE,na="")
cat("usage rows",nrow(x),"seasons",min(x$season),max(x$season),"\n")
print(aggregate(opportunity_per_game~position,data=x,FUN=function(v)c(n=length(v),mean=mean(v),median=median(v))))
