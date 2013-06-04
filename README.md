RepBot
======

Simple IRC reputation bot

======

A RepBot configuration file is a JSON file that allows the following arguments:

Name        | Type     | Description
------------|----------|-----------------------------------------------------------------
`server`    | string   | The server to connect to
`port`      | int      | The port to use
`channels`  | string[] | The list of channels to connect to
`ssl`       | bool     | True to use SSL, False to disable
`admins`    | string[] | List of usernames who are able to control RepBot
`ignore`    | string[] | List of usernames that RepBot will ignore orders from
`replimit`  | int      | The number of rep adjustments a user can make before timing out
`timelimit` | float    | The time in seconds for a rep "use" to become available again
`nick`      | string   | Nickname to use
`realname`  | string   | The "real name" for RepBot
`servname`  | string   | The "server name" for RepBot
