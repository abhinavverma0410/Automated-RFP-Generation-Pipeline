from sqlalchemy import Column, String, Text, DateTime, Boolean
# Column — defines a single column in a database table
# Every attribute in your model class is wrapped in Column()

# String — maps to VARCHAR in PostgreSQL
# Used for short text fields like title, organization, reference_number

# Text — maps to TEXT in PostgreSQL
# Used for long text fields like description and draft_content
# Unlike String, Text has no length limit

# DateTime — maps to TIMESTAMP in PostgreSQL
# Used for created_at fields that store date and time

# Boolean — maps to BOOLEAN in PostgreSQL
# Used for is_amended and proposal_drafted flags (True/False)

from sqlalchemy.sql import func
# func gives you access to SQL functions.
# We use func.now() to automatically set 'created_at' to the current timestamp
# when a new row is inserted — you never have to set it manually

from core.database import Base
# Import the Base class we defined in database.py
# Every model class inherits from Base so SQLAlchemy knows it's a table
# Without inheriting Base, the class is just a plain Python class with no database mapping

# Tender table — stores raw data scraped from CanadaBuys
# Each row represents one unique government tender
class Tender(Base):
    __tablename__ = "tenders" # Name of the table in PostgreSQL
    
    # Primary key — unique identifier for each tender from the government portal
    # Automatically rejects duplicate tenders with the same reference number
    reference_number = Column(String, primary_key=True, index=True)
    
    title = Column(String, nullable=False)  # Title of the tender, required field
    organization = Column(String)           # Government body that issued the tender
    closing_date = Column(String)           # Deadline for bid submission
    description = Column(Text)              # Full tender description scraped from detail page
    source_link = Column(String)            # Direct URL to the tender on CanadaBuys
    is_amended = Column(Boolean, default=False)        # True if tender has been amended on the website
    proposal_drafted = Column(Boolean, default=False)  # True if AI proposal has been generated
    
    created_at = Column(DateTime, default=func.now()) # Automatically records when this tender was inserted into the database

# Proposal table — stores AI-generated draft responses for each tender
class Proposal(Base):
    __tablename__ = "proposals"  # Name of the table in PostgreSQL
    
    # Links back to the tender this proposal was generated for
    reference_number = Column(String, primary_key=True, index=True)
    
    draft_content = Column(Text)  # The full AI-generated proposal text
    
    edited_content = Column(Text)       # User edited version
    status = Column(String, default="draft")
    # Status flow:
    # "draft"     = just generated, not edited yet
    # "edited"    = user has made edits
    # "submitted" = user submitted to admin for review
    # "approved"  = admin approved
    # "rejected"  = admin rejected
    submitted_by = Column(String)       # Clerk user ID of who submitted
    submitted_at = Column(DateTime)     # When it was submitted
    
    created_at = Column(DateTime, default=func.now()) # Automatically records when this draft was generated
    
    rejected_at = Column(DateTime, nullable=True) # Automatically set when admin rejects a proposal
    # Used to calculate 30-day deletion countdown
    # Auto-deletion runs when datetime.now() - rejected_at > 30 days