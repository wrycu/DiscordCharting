from flask import Flask
from discord_charting.controllers import discord_charting

app = Flask(__name__)
app.config.from_object('config')


@app.errorhandler(404)
def not_found():
    return 'Not found, bubs', 404

app.register_blueprint(discord_charting)
