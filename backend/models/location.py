"""Location models and data for Spyfall game"""
from dataclasses import dataclass
from typing import List


@dataclass
class Location:
    name: str
    roles: List[str]


# Game locations with their specific roles (from rulebook)
LOCATIONS = [
    Location("Airplane", ["Pilot", "Flight Attendant", "Passenger", "Air Marshal", "Mechanic", "Tourist", "Businessman"]),
    Location("Amusement Park", ["Ride Operator", "Parent", "Food Vendor", "Teenager", "Janitor", "Security Guard", "Mascot"]),
    Location("Bank", ["Teller", "Security Guard", "Manager", "Customer", "Robber", "Consultant", "Armored Car Driver"]),
    Location("Beach", ["Lifeguard", "Surfer", "Photographer", "Tourist", "Ice Cream Vendor", "Kite Surfer", "Beach Volleyball Player"]),
    Location("Carnival", ["Ring Toss Operator", "Visitor", "Fire Eater", "Fortune Teller", "Bouncer", "Candy Seller", "Clown"]),
    Location("Casino", ["Dealer", "Gambler", "Security", "Cocktail Waitress", "Pit Boss", "Card Counter", "Slot Machine Addict"]),
    Location("Circus Tent", ["Acrobat", "Animal Trainer", "Magician", "Fire Eater", "Clown", "Juggler", "Ringmaster"]),
    Location("Corporate Party", ["CEO", "Manager", "Employee", "Secretary", "Security", "Bartender", "Caterer"]),
    Location("Crusader Army", ["Knight", "Archer", "Priest", "Peasant", "Squire", "Cook", "Prisoner"]),
    Location("Day Spa", ["Masseuse", "Customer", "Dermatologist", "Beautician", "Receptionist", "Aromatherapist", "Manicurist"]),
    Location("Embassy", ["Ambassador", "Security Officer", "Tourist", "Refugee", "Diplomat", "Government Official", "Secretary"]),
    Location("Hospital", ["Doctor", "Nurse", "Patient", "Surgeon", "Anesthesiologist", "Intern", "Therapist"]),
    Location("Hotel", ["Guest", "Bellhop", "Manager", "Housekeeper", "Bartender", "Doorman", "Concierge"]),
    Location("Military Base", ["Soldier", "Medic", "Engineer", "Sniper", "Officer", "Tank Operator", "Radioman"]),
    Location("Movie Studio", ["Director", "Actor", "Cameraman", "Producer", "Sound Engineer", "Stuntman", "Make-up Artist"]),
    Location("Nightclub", ["DJ", "Bouncer", "Dancer", "Bartender", "VIP", "Party Girl", "Waiter"]),
    Location("Ocean Liner", ["Captain", "Bartender", "Musician", "Wealthy Passenger", "Poor Passenger", "Waiter", "Lifeguard"]),
    Location("Passenger Train", ["Mechanic", "Border Patrol", "Passenger", "Restaurant Chef", "Engineer", "Stoker", "Conductor"]),
    Location("Pirate Ship", ["Captain", "Mate", "Cabin Boy", "Gunner", "Cook", "Prisoner", "Sailor"]),
    Location("Police Station", ["Detective", "Lawyer", "Journalist", "Criminalist", "Archivist", "Patrol Officer", "Criminal"]),
    Location("Polar Station", ["Medic", "Expedition Leader", "Biologist", "Radioman", "Hydrologist", "Meteorologist", "Geologist"]),
    Location("Restaurant", ["Musician", "Customer", "Bouncer", "Hostess", "Head Chef", "Food Critic", "Waiter"]),
    Location("School", ["Gym Teacher", "Student", "Principal", "Security Guard", "Janitor", "Lunch Lady", "Maintenance Man"]),
    Location("Service Station", ["Manager", "Tire Specialist", "Biker", "Car Owner", "Car Wash Operator", "Electrician", "Auto Mechanic"]),
    Location("Space Station", ["Engineer", "Alien", "Space Tourist", "Pilot", "Commander", "Scientist", "Doctor"]),
    Location("Submarine", ["Cook", "Commander", "Sonar Technician", "Electronics Specialist", "Sailor", "Radioman", "Navigator"]),
    Location("Supermarket", ["Customer", "Cashier", "Butcher", "Janitor", "Security Guard", "Food Sample Demonstrator", "Shelf Stocker"]),
    Location("Theater", ["Coat Check Lady", "Prompter", "Cashier", "Director", "Actor", "Crewman", "Audience Member"]),
    Location("University", ["Graduate Student", "Professor", "Dean", "Psychologist", "Maintenance Man", "Student", "Janitor"]),
    Location("Zoo", ["Zookeeper", "Visitor", "Photographer", "Child", "Veterinarian", "Tour Guide", "Security Guard"])
]
