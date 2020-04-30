-- Note: Code may miss a few double headers played on the same day.
SELECT 
	count( DISTINCT date(Time) ) as NumberOfTorAwayGames
FROM baseball.Games 
where AwayTeam = 'TOR'