-- Note: This code may miss a few double headers played on the same day.
SELECT 
	count( DISTINCT HomeTeam, AwayTeam, date(Time) ) as NumberOfGames
FROM baseball.Games 