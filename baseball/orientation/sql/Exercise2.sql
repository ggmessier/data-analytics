-- Note: Code may miss a few double headers played on the same day.
SELECT 
	count( DISTINCT date(Time) ) as NumberOfNyaHomeGames
FROM baseball.Games 
where HomeTeam = 'NYA'