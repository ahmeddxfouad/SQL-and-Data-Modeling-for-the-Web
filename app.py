#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
import logging
from logging import Formatter, FileHandler
from sqlalchemy import and_
from forms import *
from flask_migrate import Migrate
from datetime import datetime
from model import db, Venue, Show, Artist

# from models import db, Venue, Artist, Show

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db.init_app(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')

#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  data = []
  rows = db.session.query(Venue.city, Venue.state).distinct().all()
  now = datetime.utcnow()
  for city, state in rows:
    venues_in_area = Venue.query.filter_by(city=city, state=state).order_by(Venue.name).all()
    items = []
    for v in venues_in_area:
      upcoming = Show.query.filter(Show.venue_id == v.id, Show.start_time > now).count()
      items.append({"id": v.id, "name": v.name, "num_upcoming_shows": upcoming})
    data.append({"city": city, "state": state, "venues": items})
  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  term = request.form.get('search_term', '')
  results = Venue.query.filter(Venue.name.ilike(f"%{term}%")).all()
  now = datetime.utcnow()
  response = {
    "count": len(results),
    "data": [
      {
        "id": v.id,
        "name": v.name,
        "num_upcoming_shows": Show.query.filter(Show.venue_id == v.id, Show.start_time > now).count()
      } for v in results
    ]
  }
  return render_template('pages/search_venues.html', results=response, search_term=term)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    v = Venue.query.get_or_404(venue_id)
    now = datetime.utcnow()

    # Past shows (JOIN Show -> Artist)
    past_rows = (
        db.session.query(Show, Artist)
        .join(Artist, Show.artist_id == Artist.id)
        .filter(and_(Show.venue_id == venue_id, Show.start_time <= now))
        .order_by(Show.start_time.desc())
        .all()
    )

    # Upcoming shows (JOIN Show -> Artist)
    upcoming_rows = (
        db.session.query(Show, Artist)
        .join(Artist, Show.artist_id == Artist.id)
        .filter(and_(Show.venue_id == venue_id, Show.start_time > now))
        .order_by(Show.start_time.asc())
        .all()
    )

    past = [{
        "artist_id": a.id,
        "artist_name": a.name,
        "artist_image_link": a.image_link,
        "start_time": s.start_time.strftime("%Y-%m-%d %H:%M:%S")
    } for (s, a) in past_rows]

    upcoming = [{
        "artist_id": a.id,
        "artist_name": a.name,
        "artist_image_link": a.image_link,
        "start_time": s.start_time.strftime("%Y-%m-%d %H:%M:%S")
    } for (s, a) in upcoming_rows]

    data = {
        "id": v.id,
        "name": v.name,
        "genres": v.genres,
        "address": v.address,
        "city": v.city,
        "state": v.state,
        "phone": v.phone,
        "website": v.website_link,
        "facebook_link": v.facebook_link,
        "seeking_talent": v.seeking_talent,
        "seeking_description": v.seeking_description,
        "image_link": v.image_link,
        "past_shows": past,
        "upcoming_shows": upcoming,
        "past_shows_count": len(past),
        "upcoming_shows_count": len(upcoming),
    }
    return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  form = VenueForm()
  if not form.validate_on_submit():
    flash('Please fix form errors and try again.')
    flash(str(form.errors))
    return render_template('forms/new_venue.html', form=form)

  try:
    v = Venue(
      name=form.name.data,
      city=form.city.data,
      state=form.state.data,
      address=form.address.data,
      phone=form.phone.data,
      image_link=form.image_link.data,
      facebook_link=form.facebook_link.data,
      website_link=form.website_link.data,
      seeking_talent=form.seeking_talent.data or False,
      seeking_description=form.seeking_description.data,
      genres=form.genres.data,
    )
    db.session.add(v)
    db.session.commit()
    flash(f'Venue {v.name} was successfully listed!')
  except Exception:
    db.session.rollback()
    flash('An error occurred. Venue could not be listed.')
  finally:
    db.session.close()
  return redirect(url_for('venues'))


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # TODO: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepages
  venue = Venue.query.get_or_404(venue_id)
  try:
      db.session.delete(venue)
      db.session.commit()
      flash(f'Venue {venue.name} was successfully deleted.')
      return '', 204  # useful for fetch() calls
  except Exception:
      db.session.rollback()
      flash('An error occurred. Venue could not be deleted.')
      return '', 500
  finally:
      db.session.close()

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data = [{"id": a.id, "name": a.name} for a in Artist.query.order_by(Artist.name).all()]
  return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
  term = request.form.get('search_term', '')
  results = Artist.query.filter(Artist.name.ilike(f"%{term}%")).all()
  now = datetime.utcnow()
  response = {
    "count": len(results),
    "data": [{
      "id": a.id,
      "name": a.name,
      "num_upcoming_shows": Show.query.filter(Show.artist_id == a.id, Show.start_time > now).count()
    } for a in results]
  }
  return render_template('pages/search_artists.html', results=response, search_term=term)


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    a = Artist.query.get_or_404(artist_id)
    now = datetime.utcnow()

    past_rows = (
        db.session.query(Show, Venue)
        .join(Venue, Show.venue_id == Venue.id)
        .filter(and_(Show.artist_id == artist_id, Show.start_time <= now))
        .order_by(Show.start_time.desc())
        .all()
    )

    upcoming_rows = (
        db.session.query(Show, Venue)
        .join(Venue, Show.venue_id == Venue.id)
        .filter(and_(Show.artist_id == artist_id, Show.start_time > now))
        .order_by(Show.start_time.asc())
        .all()
    )

    past = [{
        "venue_id": v.id,
        "venue_name": v.name,
        "venue_image_link": v.image_link,
        "start_time": s.start_time.strftime("%Y-%m-%d %H:%M:%S")
    } for (s, v) in past_rows]

    upcoming = [{
        "venue_id": v.id,
        "venue_name": v.name,
        "venue_image_link": v.image_link,
        "start_time": s.start_time.strftime("%Y-%m-%d %H:%M:%S")
    } for (s, v) in upcoming_rows]

    data = {
        "id": a.id,
        "name": a.name,
        "genres": a.genres,
        "city": a.city,
        "state": a.state,
        "phone": a.phone,
        "website": a.website_link,
        "facebook_link": a.facebook_link,
        "seeking_venue": a.seeking_venue,
        "seeking_description": a.seeking_description,
        "image_link": a.image_link,
        "past_shows": past,
        "upcoming_shows": upcoming,
        "past_shows_count": len(past),
        "upcoming_shows_count": len(upcoming),
    }
    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get_or_404(artist_id)

    form.process(obj=artist)
    return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
  form = ArtistForm()
  artist = Artist.query.get_or_404(artist_id)

  if not form.validate_on_submit():
      flash('Please fix form errors and try again.')
      flash(str(form.errors))
      return render_template('forms/edit_artist.html', form=form, artist=artist)

  try:
      artist.name = form.name.data
      artist.city = form.city.data
      artist.state = form.state.data
      artist.phone = form.phone.data
      artist.image_link = form.image_link.data
      artist.facebook_link = form.facebook_link.data
      artist.website_link = form.website_link.data
      artist.seeking_venue = form.seeking_venue.data or False
      artist.seeking_description = form.seeking_description.data
      artist.genres = form.genres.data  # list stays list/ARRAY

      db.session.commit()
      flash(f'Artist {artist.name} was successfully updated!')
  except Exception:
      db.session.rollback()
      flash('An error occurred. Artist could not be updated.')
  finally:
      db.session.close()

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get_or_404(venue_id)

    form.process(obj=venue)  # genres already list/ARRAY
    return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  form = VenueForm()
  venue = Venue.query.get_or_404(venue_id)

  if not form.validate_on_submit():
      flash('Please fix form errors and try again.')
      flash(str(form.errors))
      return render_template('forms/edit_venue.html', form=form, venue=venue)

  try:
      venue.name = form.name.data
      venue.city = form.city.data
      venue.state = form.state.data
      venue.address = form.address.data
      venue.phone = form.phone.data
      venue.image_link = form.image_link.data
      venue.facebook_link = form.facebook_link.data
      venue.website_link = form.website_link.data
      venue.seeking_talent = form.seeking_talent.data or False
      venue.seeking_description = form.seeking_description.data
      venue.genres = form.genres.data  # list/ARRAY

      db.session.commit()
      flash(f'Venue {venue.name} was successfully updated!')
  except Exception:
      db.session.rollback()
      flash('An error occurred. Venue could not be updated.')
  finally:
      db.session.close()

  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  form = ArtistForm()
  if not form.validate_on_submit():
    flash('Please fix form errors and try again.')
    flash(str(form.errors))
    return render_template('forms/new_artist.html', form=form)

  try:
    a = Artist(
      name=form.name.data,
      city=form.city.data,
      state=form.state.data,
      phone=form.phone.data,
      image_link=form.image_link.data,
      facebook_link=form.facebook_link.data,
      website_link=form.website_link.data,
      seeking_venue=form.seeking_venue.data or False,
      seeking_description=form.seeking_description.data,
      genres=form.genres.data,
    )
    db.session.add(a)
    db.session.commit()
    flash(f'Artist {a.name} was successfully listed!')
  except Exception:
    db.session.rollback()
    flash('An error occurred. Artist could not be listed.')
  finally:
    db.session.close()
  return redirect(url_for('artists'))

@app.route('/artists/<int:artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
  artist = Artist.query.get_or_404(artist_id)
  try:
    db.session.delete(artist)
    db.session.commit()
    flash(f'Artist {artist.name} was successfully deleted.')
    return '', 204
  except Exception:
    db.session.rollback()
    flash('An error occurred. Artist could not be deleted.')
    return '', 500
  finally:
    db.session.close()


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  shows = Show.query.order_by(Show.start_time.desc()).all()
  data = [{
    "venue_id": s.venue.id,
    "venue_name": s.venue.name,
    "artist_id": s.artist.id,
    "artist_name": s.artist.name,
    "artist_image_link": s.artist.image_link,
    "start_time": s.start_time.strftime("%Y-%m-%d %H:%M:%S")
  } for s in shows]
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create', methods=['GET'])
def create_shows():
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  form = ShowForm()
  if not form.validate_on_submit():
    flash('Please fix form errors and try again.')
    flash(str(form.errors))
    return render_template('forms/new_show.html', form=form)

  try:
    s = Show(
      artist_id=form.artist_id.data,
      venue_id=form.venue_id.data,
      start_time=form.start_time.data
    )
    db.session.add(s)
    db.session.commit()
    flash('Show was successfully listed!')
  except Exception:
    db.session.rollback()
    flash('An error occurred. Show could not be listed.')
  finally:
    db.session.close()
  return redirect(url_for('shows'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Specify port manually:

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
