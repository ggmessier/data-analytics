SELECT 
	count(DISTINCT Games.Time) as TotalHits
FROM baseball.Games as Games
where Games.Event = 'Hit'
