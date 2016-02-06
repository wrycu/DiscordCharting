from flask import Blueprint, render_template

discord_charting = Blueprint(
    'discord_charting',
    __name__,
    url_prefix='/',
)


@discord_charting.route('/', methods=['GET'])
def landing():
    return render_template('base.html')
