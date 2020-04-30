load data local
     infile 'Season-2018.csv'
     into table Games
     fields terminated by ','
     ignore 1 lines
     (Time,HomeTeam,AwayTeam,Inning,TopBottom,HomeScore,AwayScore,
     PlayerId,Position,PlayerTeam,Event,PitchCount,
     @vRbi,@vStartBase,@vEndBase,@vOuts,@vPlayers)
     set
	Rbi = nullif(@vRbi,''),
	StartBase = nullif(@vStartBase,''),
	EndBase = nullif(@vEndBase,''),
	Outs = nullif(@vOuts,''),
	Players = nullif(@vPlayers,'')
	;

