drop table if exists users;
create table users (
    id integer primary key autoincrement,
    username text not null unique,
    password text not null,
    salt text not null
);
insert into users(username, password, salt)
values (
    'moamoak',
    'eda1b367003c6dd6a3e5650a2bd02b393947e37d3f7184b736802ce7afe5c7c8',
    '123456789'
);

drop table if exists probes;
create table probes (
    id integer primary key autoincrement,
    name text not null,
    filename text not null,
    mac text not null,
    alpha float,
    beta float
);
insert into probes(name, filename, mac, alpha, beta)
values (
    'Ne pas supprimer',
    'test',
    '00:11:22:33:44:55',
    0.000192522,
    0.00000802250
);

drop table if exists alerts;
create table alerts (
    id integer primary key autoincrement,
    email text not null,
    probe_id integer not null
);
