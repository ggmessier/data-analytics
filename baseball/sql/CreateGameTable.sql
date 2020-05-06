drop table Games;
create table Games (
  Time datetime,
  HomeTeam varchar(20),
  AwayTeam varchar(20),
  Inning int,
  TopBottom varchar(20),
  HomeScore int,
  AwayScore int,
  PlayerId varchar(20),
  Position varchar(20),
  PlayerTeam varchar(20),
  Event varchar(20),
  PitchCount int,
  Rbi int,
  StartBase int,
  EndBase int,
  Outs int,
  Players int);
