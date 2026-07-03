import asyncio
import sys
import os
import uuid

# Ensure the app module can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import select
from app.db.session import engine
from app.models.services import ServiceCategory

CATEGORIES = [
    # Home Improvement & Maintenance
    "Plumber", "Electrician", "HVAC Technician", "Handyman", "Painter", "Roofer", "Carpenter", "Locksmith",
    "Pest Control", "Appliance Repair", "Masonry Worker", "Flooring Installer", "Tile Setter", "Drywall Installer",
    "Insulation Contractor", "Foundation Repair", "Water Damage Restoration", "Fire Damage Restoration",
    "Mold Remediation", "Cabinet Maker", "Glass Installer", "Garage Door Technician", "Awning Installer",
    "Gutter Installer", "Chimney Sweep", "Pool Maintenance", "Hot Tub Repair", "Septic Tank Service",
    "Well Pump Repair", "Solar Panel Installer", "Home Security Installer", "Smart Home Integrator",
    "Home Inspector", "Energy Auditor", "Draftsman", "Architect", "Structural Engineer", "Land Surveyor",

    # Cleaning Services
    "House Cleaner", "Office Cleaner", "Deep Cleaning Specialist", "Carpet Cleaner", "Window Cleaner",
    "Power Washer", "Gutter Cleaner", "Janitorial Service", "Post-Construction Cleaner", "Move-In/Move-Out Cleaner",
    "Air Duct Cleaner", "Upholstery Cleaner", "Tile and Grout Cleaner", "Blind Cleaner", "Chandelier Cleaner",
    "Odor Removal Specialist", "Hoarding Cleanup", "Crime Scene Cleanup", "Biohazard Cleanup", "Trash Bin Cleaner",

    # Automotive & Vehicle
    "Mobile Mechanic", "Auto Detailer", "Towing Service", "Tire Repair", "Windshield Repair", "Motorcycle Mechanic",
    "Boat Maintenance", "RV Repair", "Bicycle Mechanic", "Locksmith (Auto)", "Battery Jump Service",
    "Paintless Dent Repair", "Car Audio Installer", "Vinyl Wrap Installer", "Auto Upholstery", "Truck Mechanic",
    "Heavy Equipment Mechanic", "Forklift Repair", "Golf Cart Repair", "Scooter Repair", "Fleet Maintenance",

    # Landscaping & Outdoors
    "Lawn Care Specialist", "Gardener", "Tree Trimmer", "Arborist", "Snow Removal Service", "Hardscaper",
    "Fence Installer", "Sprinkler System Technician", "Landscape Designer", "Weed Control Specialist",
    "Lawn Aeration", "Stump Grinding", "Pond Maintenance", "Deck Builder", "Patio Installer", "Retaining Wall Builder",
    "Outdoor Lighting Installer", "Gazebo Builder", "Shed Builder", "Greenhouse Installer", "Soil Testing",

    # Moving & Delivery
    "Local Mover", "Long Distance Mover", "Furniture Assembler", "Junk Removal Service", "Courier",
    "Grocery Delivery", "Packing Service", "Piano Mover", "Appliance Delivery", "Art & Antique Mover",
    "Dumpster Rental", "Freight Hauler", "Medical Courier", "Legal Courier", "Food Delivery Driver",
    "Package Delivery", "Vehicle Transport", "Boat Transport", "Motorcycle Transport", "Pet Transport",

    # Tech & IT Services
    "Computer Repair Technician", "Network Installer", "TV Mounter", "Phone Repair Technician",
    "Data Recovery Specialist", "IT Consultant", "Cybersecurity Analyst", "Software Developer",
    "Web Developer", "Database Administrator", "Cloud Architect", "DevOps Engineer", "System Administrator",
    "Tech Support Specialist", "Wi-Fi Installer", "Server Technician", "POS System Installer",
    "Cable Technician", "Printer Repair", "Game Console Repair", "Drone Repair", "3D Printing Service",

    # Beauty, Health & Wellness
    "Hair Stylist", "Makeup Artist", "Nail Technician", "Massage Therapist", "Barber", "Personal Trainer",
    "Yoga Instructor", "Pilates Instructor", "Dietitian", "Nutritionist", "Acupuncturist", "Chiropractor",
    "Physical Therapist", "Occupational Therapist", "Speech Therapist", "Life Coach", "Health Coach",
    "Mental Health Counselor", "Tattoo Artist", "Piercing Artist", "Esthetician", "Lash Technician",
    "Eyebrow Threader", "Waxing Specialist", "Spray Tanning", "Color Consultant", "Wardrobe Stylist",

    # Events & Entertainment
    "DJ", "Photographer", "Videographer", "Event Planner", "Caterer", "Bartender", "Florist",
    "Band/Musician", "Photo Booth Operator", "Event Security", "Valet Parking", "Party Equipment Rental",
    "Magician", "Clown", "Face Painter", "Balloon Artist", "Caricature Artist", "Master of Ceremonies",
    "Event Decorator", "Lighting Technician", "Sound Engineer", "Stagehand", "Makeup Artist (Special FX)",

    # Education & Tutoring
    "Math Tutor", "Science Tutor", "Language Tutor", "Test Prep Coach", "Music Teacher", "Art Instructor",
    "Driving Instructor", "Cooking Instructor", "Dance Teacher", "Martial Arts Instructor", "Swim Instructor",
    "Chess Coach", "Computer Skills Tutor", "Reading Tutor", "Writing Tutor", "Special Education Tutor",
    "Sign Language Instructor", "Acting Coach", "Vocal Coach", "Public Speaking Coach", "Sewing Instructor",

    # Financial & Legal
    "Tax Preparer", "Bookkeeper", "Notary Public", "Legal Consultant", "Financial Advisor", "Insurance Agent",
    "Accountant", "Payroll Specialist", "Credit Repair Specialist", "Debt Counselor", "Estate Planner",
    "Paralegal", "Process Server", "Private Investigator", "Mediator", "Grant Writer", "Business Broker",
    "Real Estate Appraiser", "Mortgage Broker", "Title Searcher", "Bail Bondsman",

    # Writing, Translation & Creative
    "Copywriter", "Proofreader", "Translator", "Resume Writer", "Graphic Designer", "Web Designer",
    "Interior Designer", "Voice Actor", "Editor", "Technical Writer", "Ghostwriter", "Blogger",
    "Content Creator", "SEO Specialist", "Illustrator", "Animator", "Video Editor", "Audio Editor",
    "Podcast Producer", "Music Producer", "Storyboard Artist", "3D Modeler", "UX/UI Designer",

    # Business & Administrative
    "Virtual Assistant", "Customer Support Rep", "Data Entry Clerk", "Social Media Manager",
    "Project Manager", "HR Consultant", "Recruiter", "Business Analyst", "Marketing Consultant",
    "PR Specialist", "Event Marketer", "Telemarketer", "Lead Generator", "Sales Consultant",
    "Operations Consultant", "Logistics Coordinator", "Supply Chain Consultant", "Inventory Counter",
    "Quality Assurance Tester", "Transcriptionist", "Interpreter", "Call Center Agent",

    # Pet Services
    "Dog Walker", "Pet Sitter", "Pet Groomer", "Dog Trainer", "Aquarium Maintainer", "Mobile Vet",
    "Pet Photographer", "Animal Behaviorist", "Pet Waste Removal", "Pet Taxi", "Equine Dentist",
    "Farrier", "Reptile Care Specialist", "Bird Sitter", "Pet Bakery", "Pet Boarding",

    # Arts, Crafts & Custom Made
    "Tailor/Seamstress", "Custom Furniture Builder", "Jewelry Maker", "Blacksmith", "Welder",
    "Potter", "Ceramicist", "Glassblower", "Woodworker", "Leatherworker", "Shoe Cobbler",
    "Watch Repair", "Clock Repair", "Upholsterer", "Calligrapher", "Engraver", "Custom Framer",
    "Knitter/Crocheter", "Quilter", "Candle Maker", "Soap Maker", "Perfumer",

    # Real Estate & Property
    "Real Estate Agent", "Property Manager", "Leasing Agent", "Stager", "Real Estate Photographer",
    "Title Agent", "Escrow Officer", "Foreclosure Specialist", "HOA Manager", "Tenant Screener",

    # Hospitality, Tourism & Transport
    "Tour Guide", "Travel Agent", "Chauffeur", "Personal Chef", "Sommelier", "Flight Instructor",
    "Boat Captain", "Ski Instructor", "Scuba Instructor", "Surfing Instructor", "Camp Counselor",
    "Bed & Breakfast Host", "Airbnb Co-host", "Translating Guide",

    # Retail & E-commerce
    "Personal Shopper", "Merchandiser", "Mystery Shopper", "E-commerce Manager", "Dropshipping Consultant",
    "Shopify Expert", "Amazon Seller Consultant", "Inventory Manager", "Window Dresser", "Visual Merchandiser",

    # Environmental & Green
    "Recycling Coordinator", "Composting Service", "Solar Consultant", "Wind Turbine Technician",
    "Environmental Consultant", "Sustainability Officer", "Green Building Consultant", "Energy Broker",

    # Security & Safety
    "Security Guard", "Bodyguard", "Bouncer", "Fire Safety Inspector", "OSHA Consultant",
    "First Aid Instructor", "Self Defense Instructor", "Cyber Security Consultant", "Alarm Responder",

    # Industrial & Manufacturing
    "Machinist", "CNC Operator", "Tool and Die Maker", "Industrial Electrician", "Millwright",
    "Heavy Equipment Operator", "Crane Operator", "Rigging Specialist", "Welding Inspector",
    "Quality Control Inspector", "Packaging Engineer", "Assembly Line Worker",

    # Agriculture & Farming
    "Farm Hand", "Tractor Mechanic", "Crop Consultant", "Irrigation Specialist", "Beekeeper",
    "Shearer", "Orchard Worker", "Livestock Appraiser", "Agribusiness Consultant", "Dairy Worker",

    # Specialized Trades & Services
    "Auctioneer", "Bailiff", "Bounty Hunter", "Court Reporter", "Polygraph Examiner",
    "Genealogist", "Personal Archivist", "Home Organizer", "Decluttering Expert", "Feng Shui Consultant",
    "Art Appraiser", "Antique Restorer", "Bookbinder", "Luthier (Guitar Maker)", "Piano Tuner",
    "Taxidermist", "Locksmith (Safe/Vault)", "Elevator Mechanic", "Escalator Mechanic", "Neon Sign Maker",
    "Glass Blower", "Sail Maker", "Tent Installer", "Scaffolding Erector", "Demolition Specialist",
    "Asbestos Removal", "Lead Paint Removal", "Radon Mitigation", "Waterproofing Specialist",
    "Soundproofing Contractor", "Epoxy Flooring Installer", "Concrete Polisher", "Asphalt Paver",
    "Line Striper", "Street Sweeper", "Parking Lot Attendant", "Valet Manager", "Car Wash Attendant",
    "Gas Station Attendant", "Toll Booth Operator", "Meter Reader", "Process Automation Specialist",
    "Robotics Technician", "Drone Pilot", "Surveyor Assistant", "Map Maker (Cartographer)",
    "Meteorologist (Private)", "Statistician", "Actuary", "Cryptographer", "Ethical Hacker",
    "Penetration Tester", "Blockchain Developer", "Smart Contract Auditor", "NFT Consultant",
    "Crypto Trader", "Forex Trader", "Day Trader", "Investment Banker", "Venture Capitalist",
    "Angel Investor", "Fundraiser", "Grant Evaluator", "Non-Profit Consultant", "Volunteer Coordinator",
    "Community Manager", "Forum Moderator", "Discord Manager", "Twitch Mod", "E-sports Coach",
    "Gamer (Professional)", "Streamer", "YouTuber", "Vlogger", "Influencer", "Brand Ambassador",
    "Mystery Reader", "Tarot Reader", "Astrologer", "Psychic", "Numerologist", "Handwriting Analyst",
    "Hypnotherapist", "Reiki Healer", "Energy Healer", "Crystal Healer", "Sound Bath Facilitator",
    "Doula", "Midwife", "Lactation Consultant", "Sleep Trainer", "Baby Proofer", "Nanny",
    "Au Pair", "Babysitter", "Elder Caregiver", "Hospice Worker", "Grief Counselor", "Funeral Director",
    "Embalmer", "Crematory Operator", "Cemetery Worker", "Monument Maker", "Florist (Funeral)",
    "Marriage Celebrant", "Wedding Officiant", "Divorce Coach", "Co-parenting Counselor",
    "Relationship Coach", "Dating Coach", "Matchmaker", "Image Consultant", "Etiquette Coach",
    "Voice Coach", "Dialect Coach", "Acting Double", "Stunt Double", "Hand Model", "Foot Model",
    "Fit Model", "Runway Model", "Commercial Model", "Voiceover Artist", "Audiobook Narrator",
    "Foley Artist", "Sound Designer", "Colorist (Film)", "Special Effects Artist", "Prop Maker",
    "Set Designer", "Location Scout", "Casting Director", "Talent Agent", "Literary Agent",
    "Art Dealer", "Gallery Curator", "Museum Guide", "Docent", "Archivist", "Librarian",
    "Researcher", "Fact Checker", "Indexer", "Bibliographer", "Genealogy Researcher", "Heir Searcher",
    "Skip Tracer", "Repossession Agent", "Process Server", "Private Eye", "Undercover Investigator",
    "Loss Prevention Specialist", "Store Detective", "Secret Shopper", "Quality Auditor",
    "ISO Auditor", "Compliance Officer", "Risk Manager", "Safety Officer", "Ergonomist",
    "Industrial Hygienist", "Toxicologist", "Epidemiologist", "Public Health Consultant",
    "Biostatistician", "Clinical Data Manager", "Medical Writer", "Regulatory Affairs Specialist",
    "Pharmacovigilance Specialist", "Clinical Trial Coordinator", "Phlebotomist", "ECG Technician",
    "Ultrasound Technician", "Radiologic Technologist", "MRI Technologist", "Nuclear Medicine Technologist",
    "Radiation Therapist", "Dosimetrist", "Medical Physicist", "Biomedical Equipment Technician",
    "Surgical Technologist", "Sterile Processing Technician", "Medical Laboratory Scientist",
    "Cytotechnologist", "Histotechnologist", "Pathologist Assistant", "Medical Coder", "Medical Biller",
    "Health Information Manager", "Medical Transcriptionist", "Dental Assistant", "Dental Hygienist",
    "Dental Laboratory Technician", "Orthodontic Assistant", "Optician", "Ophthalmic Technician",
    "Optometric Assistant", "Audiology Assistant", "Speech-Language Pathology Assistant",
    "Physical Therapist Assistant", "Occupational Therapy Assistant", "Massage Therapy Instructor",
    "Esthetics Instructor", "Cosmetology Instructor", "Barbering Instructor", "Nail Technology Instructor",
    "Makeup Artistry Instructor", "Tattoo Apprenticeship Mentor", "Piercing Apprenticeship Mentor",
    "Dog Training Mentor", "Horse Training Mentor", "Falconry Sponsor", "Beekeeping Mentor",
    "Master Gardener", "Compost Master", "Permaculture Designer", "Foraging Guide", "Hunting Guide",
    "Fishing Guide", "Whitewater Rafting Guide", "Mountaineering Guide", "Rock Climbing Guide",
    "Caving Guide", "Skydiving Instructor", "Paragliding Instructor", "Hang Gliding Instructor",
    "Hot Air Balloon Pilot", "Helicopter Pilot", "Charter Pilot", "Flight Dispatcher",
    "Air Traffic Controller", "Aircraft Mechanic", "Avionics Technician", "Ramp Agent",
    "Baggage Handler", "Flight Attendant", "Cruise Ship Worker", "Yacht Crew", "Marina Attendant",
    "Dockmaster", "Harbormaster", "Lockmaster", "Lighthouse Keeper", "Park Ranger",
    "Forest Ranger", "Wildlife Biologist", "Botanist", "Zoologist", "Marine Biologist",
    "Oceanographer", "Geologist", "Seismologist", "Volcanologist", "Meteorologist",
    "Climatologist", "Astronomer", "Astrophysicist", "Cosmologist", "Space Scientist",
    "Planetary Scientist", "Astrobiologist", "Aerospace Engineer", "Naval Architect",
    "Marine Engineer", "Nuclear Engineer", "Petroleum Engineer", "Mining Engineer",
    "Geological Engineer", "Materials Engineer", "Ceramic Engineer", "Metallurgical Engineer",
    "Polymer Engineer", "Plastics Engineer", "Textile Engineer", "Agricultural Engineer",
    "Biomedical Engineer", "Clinical Engineer", "Rehabilitation Engineer", "Ergonomics Engineer",
    "Human Factors Engineer", "Systems Engineer", "Industrial Engineer", "Manufacturing Engineer",
    "Production Engineer", "Quality Engineer", "Reliability Engineer", "Safety Engineer",
    "Fire Protection Engineer", "Environmental Engineer", "Sanitary Engineer", "Water Resources Engineer",
    "Hydraulic Engineer", "Coastal Engineer", "Transportation Engineer", "Traffic Engineer",
    "Highway Engineer", "Railway Engineer", "Airport Engineer", "Tunnel Engineer",
    "Bridge Engineer", "Structural Engineer", "Geotechnical Engineer", "Foundation Engineer",
    "Earthquake Engineer", "Wind Engineer", "Civil Engineer", "Construction Engineer",
    "Architectural Engineer", "Building Services Engineer", "Acoustical Engineer", "Illumination Engineer"
]

# De-duplicate just in case
CATEGORIES = list(set(CATEGORIES))

async def seed():
    print(f"Total categories loaded: {len(CATEGORIES)}")
    async with AsyncSession(engine) as session:
        added = 0
        skipped = 0
        for cat_name in CATEGORIES:
            # Check if category already exists
            stmt = select(ServiceCategory).where(ServiceCategory.name == cat_name)
            result = await session.execute(stmt)
            existing_cat = result.scalar_one_or_none()
            
            if not existing_cat:
                new_cat = ServiceCategory(
                    id=uuid.uuid4(),
                    name=cat_name,
                    description=f"Professional {cat_name} services.",
                    icon="Briefcase"
                )
                session.add(new_cat)
                added += 1
            else:
                skipped += 1
                
        await session.commit()
        print(f"Categories Seeded: {added} added, {skipped} skipped (already existed).")

if __name__ == "__main__":
    asyncio.run(seed())
