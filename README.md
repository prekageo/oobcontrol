oobcontrol: Control Out Of Band
===============================


Presentation
------------

`oobcontrol` is an interactive command-line tool for controlling out-of-band management devices.

It supports the following devices:
* Dell iDRAC7
* Intel Integrated BMC Web Console

It supports the following functions:
* Console
* Reboot

If you need broader support for devices and/or functions, please take a look at [moob](https://github.com/spotify/moob/).

The configuration file `~/.oobcontrol` is required. Its contents look like this:

```
[params]
java = javaw

[friendlyname]
type = Idrac
host = server.company.com
username = user
password = foo
```

* `params.java` specify the java executable to invoke for displaying the console.
* Sections represent individual servers which are identified by a `friendlyname`.
  * `type` can be either `Idrac` or `Intel`.
  * `host`, `username` and `password` are self-explanatory.

Installation
------------

`oobcontrol` is written in Python. You can just copy it somewhere in your `$PATH`. You also need to create the configuration file `~/.oobcontrol`.

Usage
-----

The tool is interactive so you just need to invoke it:

        # oobcontrol
