#!/bin/bash
source .venv/bin/activate;
avn user login dhata4248@gmail.com --token;
avn service update craftdb --power-on;
avn service wait craftdb;
flask run;