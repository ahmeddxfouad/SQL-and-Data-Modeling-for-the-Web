from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime

db = SQLAlchemy()

class Show(db.Model):
    __tablename__ = "shows"
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey("artists.id", ondelete="CASCADE"), nullable=False)
    venue_id  = db.Column(db.Integer, db.ForeignKey("venues.id",  ondelete="CASCADE"), nullable=False)
    artist = db.relationship("Artist", back_populates="shows")
    venue  = db.relationship("Venue",  back_populates="shows")

    @staticmethod
    def upcoming_count_for_venue(venue_id, now=None):
        now = now or datetime.utcnow()
        return Show.query.filter(Show.venue_id == venue_id, Show.start_time > now).count()

    @staticmethod
    def upcoming_count_for_artist(artist_id, now=None):
        now = now or datetime.utcnow()
        return Show.query.filter(Show.artist_id == artist_id, Show.start_time > now).count()

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
    genres = db.Column(ARRAY(db.String()), nullable=False)
    shows = db.relationship("Show", back_populates="venue", cascade="all, delete-orphan")

    __table_args__ = (db.UniqueConstraint("name", "city", "state", name="uq_venue_name_city_state"),)

    # ---- Encapsulated queries ----
    @staticmethod
    def distinct_cities_states():
        return db.session.query(Venue.city, Venue.state).distinct().all()

    @staticmethod
    def by_city_state(city, state):
        return Venue.query.filter_by(city=city, state=state).order_by(Venue.name).all()

    @staticmethod
    def search_by_name(term):
        return Venue.query.filter(Venue.name.ilike(f"%{term}%")).all()

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

    __table_args__ = (db.UniqueConstraint("name", "city", "state", name="uq_artist_name_city_state"),)

    # ---- Encapsulated queries ----
    @staticmethod
    def list_all():
        return Artist.query.order_by(Artist.name).all()

    @staticmethod
    def search_by_name(term):
        return Artist.query.filter(Artist.name.ilike(f"%{term}%")).all()

    def past_and_upcoming_shows(self, now=None):
        now = now or datetime.utcnow()
        past = Show.query.filter(Show.artist_id == self.id, Show.start_time <= now).order_by(Show.start_time.desc()).all()
        upcoming = Show.query.filter(Show.artist_id == self.id, Show.start_time > now).order_by(Show.start_time.asc()).all()
        return past, upcoming
