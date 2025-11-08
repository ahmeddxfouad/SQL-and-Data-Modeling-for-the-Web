#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# TODO: connect to a local postgresql database

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Show(db.Model):
    __tablename__ = "shows"
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)

    artist_id = db.Column(db.Integer, db.ForeignKey("artists.id", ondelete="CASCADE"), nullable=False)
    venue_id  = db.Column(db.Integer, db.ForeignKey("venues.id",  ondelete="CASCADE"), nullable=False)

    # Convenient joins
    artist = db.relationship("Artist", back_populates="shows")
    venue  = db.relationship("Venue",  back_populates="shows")

    def __repr__(self):
        return f"<Show id={self.id} artist_id={self.artist_id} venue_id={self.venue_id}>"


class Venue(db.Model):
    __tablename__ = "venues"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(500))
    website_link = db.Column(db.String(500))
    seeking_talent = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.String(500))
    # Keep genres as a comma-separated string (beginner-friendly & portable)
    genres = db.Column(ARRAY(db.String()), nullable=False)

    # one-to-many via Show
    shows = db.relationship("Show", back_populates="venue", cascade="all, delete-orphan")

    # Basic “uniqueness” to prevent obvious duplicates (not required, but helpful)
    __table_args__ = (
        db.UniqueConstraint("name", "city", "state", name="uq_venue_name_city_state"),
    )

    def __repr__(self):
        return f"<Venue id={self.id} name={self.name}>"


class Artist(db.Model):
    __tablename__ = "artists"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(500))
    website_link = db.Column(db.String(500))
    seeking_venue = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.String(500))
    genres = db.Column(ARRAY(db.String()), nullable=False)

    shows = db.relationship("Show", back_populates="artist", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("name", "city", "state", name="uq_artist_name_city_state"),
    )

    def __repr__(self):
        return f"<Artist id={self.id} name={self.name}>"

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
  past = Show.query.filter(Show.venue_id == v.id, Show.start_time <= now).order_by(Show.start_time.desc()).all()
  upcoming = Show.query.filter(Show.venue_id == v.id, Show.start_time > now).order_by(Show.start_time.asc()).all()

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
    "past_shows": [{
      "artist_id": s.artist.id,
      "artist_name": s.artist.name,
      "artist_image_link": s.artist.image_link,
      "start_time": s.start_time.strftime("%Y-%m-%d %H:%M:%S")
    } for s in past],
    "upcoming_shows": [{
      "artist_id": s.artist.id,
      "artist_name": s.artist.name,
      "artist_image_link": s.artist.image_link,
      "start_time": s.start_time.strftime("%Y-%m-%d %H:%M:%S")
    } for s in upcoming],
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
  # clicking that button delete it from the db then redirect the user to the homepage
  return None

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
  past = Show.query.filter(Show.artist_id == a.id, Show.start_time <= now).order_by(Show.start_time.desc()).all()
  upcoming = Show.query.filter(Show.artist_id == a.id, Show.start_time > now).order_by(Show.start_time.asc()).all()
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
    "past_shows": [{
      "venue_id": s.venue.id,
      "venue_name": s.venue.name,
      "venue_image_link": s.venue.image_link,
      "start_time": s.start_time.strftime("%Y-%m-%d %H:%M:%S")
    } for s in past],
    "upcoming_shows": [{
      "venue_id": s.venue.id,
      "venue_name": s.venue.name,
      "venue_image_link": s.venue.image_link,
      "start_time": s.start_time.strftime("%Y-%m-%d %H:%M:%S")
    } for s in upcoming],
    "past_shows_count": len(past),
    "upcoming_shows_count": len(upcoming),
  }
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist={
    "id": 4,
    "name": "Guns N Petals",
    "genres": ["Rock n Roll"],
    "city": "San Francisco",
    "state": "CA",
    "phone": "326-123-5000",
    "website": "https://www.gunsnpetalsband.com",
    "facebook_link": "https://www.facebook.com/GunsNPetals",
    "seeking_venue": True,
    "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
    "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80"
  }
  # TODO: populate form with fields from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue={
    "id": 1,
    "name": "The Musical Hop",
    "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
    "address": "1015 Folsom Street",
    "city": "San Francisco",
    "state": "CA",
    "phone": "123-123-1234",
    "website": "https://www.themusicalhop.com",
    "facebook_link": "https://www.facebook.com/TheMusicalHop",
    "seeking_talent": True,
    "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
    "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60"
  }
  # TODO: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
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
