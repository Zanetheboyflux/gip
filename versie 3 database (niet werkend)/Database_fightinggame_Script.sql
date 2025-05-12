create database fightinggame_database; 

create table Pygame (
GameID int not null auto_increment, 
Winner varchar(255) not null, 
Loser varchar(255) not null, 
Player1_character varchar(255), 
Player2_character varchar(255), 
primary key (GameID)); 

alter table Pygame 
modify column Winner int ; 
alter table Pygame 
modify column Loser int ; 

alter table Pygame 
modify column Player1_character text; 
alter table Pygame 
modify column Player2_character text; 
alter table Pygame 
add timestamp datetime default current_timestamp ; 

create table users (
accountID int not null auto_increment, 
account_name varchar(255) not null, 
account_password varchar(255) not null,
primary key (accountID)
); 
alter table users 
add GameID int ; 
alter table users 
add foreign key (accountID) references pygame(GameID); 
alter table Pygame 
drop column Player1_character;  
alter table Pygame 
drop column Player2_character;  
alter table Pygame
add player_name varchar(255) not null; 
alter table Pygame 
add character_selected varchar(255) not null;
alter table users
add win_count integer default 0; 
alter table users  
add total_games integer default 0; 
alter table users 
add loss_count integer default 0; 

INSERT INTO pygame (Winner, Loser, player_name, character_selected) VALUES (2, 1, 'Player2', 'Mewtwo'); 
