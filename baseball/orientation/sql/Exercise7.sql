SELECT 
	count(DISTINCT Games.Time) as TotalHits
FROM baseball.Games as Games
left join baseball.Rosters as Rosters on Rosters.PlayerId = Games.PlayerId 
where Games.Event = 'Hit' and Rosters.LastName REGEXP 'ez$'
