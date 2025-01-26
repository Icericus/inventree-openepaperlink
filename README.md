InvenTree-OpenEPaperLink
============

A small python application that connects [OpenEPaperLink](https://github.com/OpenEPaperLink)-Screens to a [InvenTree](https://github.com/inventree)-API to show the contents of specific locations. Just gotta assign the barcode of a screen to a location and it will show the stock once the script runs the next time.

![3 EPaper displays of different sizes showing ordered stock lists](https://github.com/icericus/inventree-openepaperlink/blob/main/assets/IVT-OEPL-pic.jpg?raw=true)

# Installation
## Option 1: Docker compose

- download the docker-compose.yml and the .env file
- fill in the environment variables in .env
- run `docker-compose up -d`
- this certainly isn't pretty, but it works
- feel free to create an issue or pull request if you have a better idea on how to run the script every half an hour

## Option 2: Python

- install requirements
- Get an API key from your InvenTree instance (should have permissions to view "Parts", "Stock Items" and "Stock Locations")
- Rename the config.ini.example to config.ini and fill it out with your data
- run main.py with a cronjob or something similar

# Changing fonts

If you want to add different fonts to the software you will most likely need to change some of the text sizes and positions. To make that process a bit easier there's a debug switch in the config to disable the upload, that way you can just keep rendering the images without needing to wait for it to upload.

# ToDo

- autoscaling titlesize
- Hash comparison to only render images when necessary
- better README