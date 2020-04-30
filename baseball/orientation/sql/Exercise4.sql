SELECT 
	PlayerId, 
	sum(Rbi) as TotRbi
FROM baseball.Games 
group by PlayerId 
order by TotRbi DESC 
limit 1