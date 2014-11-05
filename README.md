
Tor Relay BerryClip+ Lights (in the absence of a better name)
=============================================================

A multithreaded [script](tor-bcl.py) to control [BerryClip+](http://www.raspberrypi-spy.co.uk/berryclip-6-led-add-on-board/berryclip-plus-instructions/) LEDs based on Tor relay bandwidth data.

## Introduction ##

The BerryClip+ is a small Raspi addon board built to provide an easy way for beginners to learn how the available GPIOs work. It contains six LEDs, two switches and one buzzer, what makes it perfect to give a glimpse of how a Tor relay is performing without the need for [arm](https://www.atagar.com/arm/).

![BerryClip+](https://raw.github.com/lzkill/tor-bcl/master/bc.jpg)


## License ##

This script may be used under the terms of the MIT License, wich a [copy](LICENSE) is included in the download.


## Dependencies ##

- [Python](https://www.python.org) 2.6 or greater
- [RPi.GPIO](https://pypi.python.org/pypi/RPi.GPIO) 0.5.2 or greater
- [Stem](https://stem.torproject.org) 1.2.2 or greater


## Features ##

- Multithreaded (switch events handled right away)
- LEDs power off/on switch
- Network drop/rise switch
- Visual indication for download and upload bandwidth, Tor state and Internet connectivity


## Usage ##

In order to run the script just type in your terminal

	$sudo python tor-bcl.py

Optionally one could set [Supervisor](http://supervisord.org) to assure that the script is always running no matter what. (see the [tor-bcl.conf](tor-bcl.conf))

Once started the script turns the BerryClip+ LEDs on and off based on the download and upload instant values the Tor relay is producing. 

- {L1,L2,L3} -> download
- {L4,L5,L6} -> upload

That's why it's a good idea to solder in a 'non-standard' way, making two green-yellow-red sequences.

While deciding which LED should be lit the script uses `RelayBandwidthBurst` and `RelayBandwidthRate` from Tor. 

![LED scheme](https://raw.github.com/lzkill/tor-bcl/master/leds.png)

The lights can be disabled / re-enabled with the black switch (S1). The red switch (S2) drops / rises the Raspiberry network interfaces.


## Your Improvements ##

If you add improvements to this code please send them to me as pull requests on GitHub. I will add them to the next release so that everyone can enjoy your work. You might also benefit from it as others may fix bugs in your source files or may continue to enhance them.

## Thanks ##

With regards from

[Luiz Kill](mailto:me@lzkill.com) and Contributors

