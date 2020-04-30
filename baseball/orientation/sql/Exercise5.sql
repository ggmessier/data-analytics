SELECT 
	Games.Time,
	Rosters.LastName,
	Rosters.FirstName,
	Rosters.TeamId as PlayerTeam
FROM baseball.Games as Games
left join baseball.Rosters as Rosters on Rosters.PlayerId = Games.PlayerId 
where Games.Event = 'Hit'
