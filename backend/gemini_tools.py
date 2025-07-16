from google.genai import types
import travel_mock_data
from travel_mock_data import USER_ID
import json
from datetime import datetime, timezone
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Helper function for structured logging
def _log_tool_event(event_type: str, tool_name: str, parameters: dict, response: dict = None):
    """Helper function to create and print a structured log entry for tool events."""
    log_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "log_type": "TOOL_EVENT",
        "event_subtype": event_type,
        "tool_function_name": tool_name,
        "parameters_sent": parameters
    }
    if response is not None:
        log_payload["response_received"] = response
    print(json.dumps(log_payload))

# Function Declaration for searchFlights
searchFlights_declaration = types.FunctionDeclaration(
    name="searchFlights",
    description="Searches for available flights based on origin, destination, and travel date.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "origin": types.Schema(type=types.Type.STRING, description="The departure city or airport code (e.g., 'Mumbai', 'BOM')."),
            "destination": types.Schema(type=types.Type.STRING, description="The arrival city or airport code (e.g., 'Dubai', 'DXB')."),
            "departure_date": types.Schema(type=types.Type.STRING, description="The departure date in YYYY-MM-DD format."),
            "passengers": types.Schema(type=types.Type.INTEGER, description="The number of passengers (defaults to 1).")
        },
        required=["origin", "destination", "departure_date"]
    )
)

# Function Declaration for bookFlight
bookFlight_declaration = types.FunctionDeclaration(
    name="bookFlight",
    description="Books a flight for the user using the flight ID from search results.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "flight_id": types.Schema(type=types.Type.STRING, description="The unique flight ID from search results."),
            "passenger_name": types.Schema(type=types.Type.STRING, description="The name of the passenger."),
            "passenger_email": types.Schema(type=types.Type.STRING, description="The email address of the passenger."),
            "passengers": types.Schema(type=types.Type.INTEGER, description="The number of passengers (defaults to 1).")
        },
        required=["flight_id", "passenger_name", "passenger_email"]
    )
)

# Function Declaration for getFlightStatus
getFlightStatus_declaration = types.FunctionDeclaration(
    name="getFlightStatus",
    description="Retrieves the current status of a booked flight using the booking ID.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "booking_id": types.Schema(type=types.Type.STRING, description="The booking reference ID for the flight.")
        },
        required=["booking_id"]
    )
)

# Function Declaration for searchHotels
searchHotels_declaration = types.FunctionDeclaration(
    name="searchHotels",
    description="Searches for available hotels in a city for specified dates.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(type=types.Type.STRING, description="The city where you want to stay."),
            "check_in_date": types.Schema(type=types.Type.STRING, description="The check-in date in YYYY-MM-DD format."),
            "check_out_date": types.Schema(type=types.Type.STRING, description="The check-out date in YYYY-MM-DD format."),
            "guests": types.Schema(type=types.Type.INTEGER, description="The number of guests (defaults to 1).")
        },
        required=["city", "check_in_date", "check_out_date"]
    )
)

# Function Declaration for bookHotel
bookHotel_declaration = types.FunctionDeclaration(
    name="bookHotel",
    description="Books a hotel room for the user using the hotel ID from search results.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "hotel_id": types.Schema(type=types.Type.STRING, description="The unique hotel ID from search results."),
            "guest_name": types.Schema(type=types.Type.STRING, description="The name of the guest."),
            "guest_email": types.Schema(type=types.Type.STRING, description="The email address of the guest."),
            "check_in_date": types.Schema(type=types.Type.STRING, description="The check-in date in YYYY-MM-DD format."),
            "check_out_date": types.Schema(type=types.Type.STRING, description="The check-out date in YYYY-MM-DD format."),
            "rooms": types.Schema(type=types.Type.INTEGER, description="The number of rooms to book (defaults to 1).")
        },
        required=["hotel_id", "guest_name", "guest_email", "check_in_date", "check_out_date"]
    )
)

# Function Declaration for getBookingDetails
getBookingDetails_declaration = types.FunctionDeclaration(
    name="getBookingDetails",
    description="Retrieves detailed information about a booking using the booking ID.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "booking_id": types.Schema(type=types.Type.STRING, description="The booking reference ID.")
        },
        required=["booking_id"]
    )
)

# Function Declaration for listUserBookings
listUserBookings_declaration = types.FunctionDeclaration(
    name="listUserBookings",
    description="Lists all bookings for the current user.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={}
    )
)

# Function Declaration for cancelBooking
cancelBooking_declaration = types.FunctionDeclaration(
    name="cancelBooking",
    description="Cancels an existing booking using the booking ID.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "booking_id": types.Schema(type=types.Type.STRING, description="The booking reference ID to cancel.")
        },
        required=["booking_id"]
    )
)

# Function Declaration for getDestinationInfo
getDestinationInfo_declaration = types.FunctionDeclaration(
    name="getDestinationInfo",
    description="Gets detailed information about a travel destination including attractions and best time to visit.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(type=types.Type.STRING, description="The destination city name.")
        },
        required=["city"]
    )
)

# Function Declaration for getWeatherInfo
getWeatherInfo_declaration = types.FunctionDeclaration(
    name="getWeatherInfo",
    description="Gets current weather and forecast information for a destination.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(type=types.Type.STRING, description="The city name for weather information.")
        },
        required=["city"]
    )
)

# Function Declaration for searchActivities
searchActivities_declaration = types.FunctionDeclaration(
    name="searchActivities",
    description="Searches for activities and attractions in a destination city.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(type=types.Type.STRING, description="The destination city name."),
            "activity_type": types.Schema(type=types.Type.STRING, description="Optional. The type of activity (e.g., 'Sightseeing', 'Adventure', 'Cultural').")
        },
        required=["city"]
    )
)

# Actual Python function implementations

async def searchFlights(origin: str, destination: str, departure_date: str, passengers: int = 1):
    tool_name = "searchFlights"
    params_sent = {"origin": origin, "destination": destination, "departure_date": departure_date, "passengers": passengers}
    _log_tool_event("INVOCATION_START", tool_name, params_sent)
    logger.info(f"[{tool_name}] Attempting to search flights from {origin} to {destination} on {departure_date}")
    
    try:
        result = travel_mock_data.search_flights(origin, destination, departure_date, passengers)
        logger.info(f"[{tool_name}] Received from travel_mock_data.search_flights: {result}")
        
        if result.get("status") == "SUCCESS":
            api_response = {
                "status": "success",
                "flights": result.get("flights", []),
                "message": f"Found {len(result.get('flights', []))} flights from {origin} to {destination}"
            }
        elif result.get("status") == "NO_FLIGHTS_FOUND":
            api_response = {
                "status": "no_results",
                "message": result.get("message", f"No flights found from {origin} to {destination}"),
                "flights": []
            }
        else:
            api_response = {
                "status": "error",
                "message": result.get("message", "Failed to search flights")
            }
    except Exception as e:
        logger.error(f"[{tool_name}] Error calling travel_mock_data.search_flights: {e}", exc_info=True)
        api_response = {"status": "error", "message": f"An internal error occurred while searching flights"}
    
    _log_tool_event("INVOCATION_END", tool_name, params_sent, api_response)
    return api_response

async def bookFlight(flight_id: str, passenger_name: str, passenger_email: str, passengers: int = 1):
    tool_name = "bookFlight"
    params_sent = {"flight_id": flight_id, "passenger_name": passenger_name, "passenger_email": passenger_email, "passengers": passengers}
    _log_tool_event("INVOCATION_START", tool_name, params_sent)
    logger.info(f"[{tool_name}] Attempting to book flight {flight_id} for {passenger_name}")
    
    try:
        result = travel_mock_data.book_flight(flight_id, passenger_name, passenger_email, passengers)
        logger.info(f"[{tool_name}] Received from travel_mock_data.book_flight: {result}")
        
        if result.get("status") == "SUCCESS":
            api_response = {
                "status": "success",
                "message": result.get("message"),
                "booking_id": result.get("booking_id"),
                "total_cost": result.get("total_cost"),
                "currency": result.get("currency")
            }
        else:
            api_response = {
                "status": "error",
                "message": result.get("message", "Failed to book flight")
            }
    except Exception as e:
        logger.error(f"[{tool_name}] Error calling travel_mock_data.book_flight: {e}", exc_info=True)
        api_response = {"status": "error", "message": "An internal error occurred while booking the flight"}
    
    _log_tool_event("INVOCATION_END", tool_name, params_sent, api_response)
    return api_response

async def getFlightStatus(booking_id: str):
    tool_name = "getFlightStatus"
    params_sent = {"booking_id": booking_id}
    _log_tool_event("INVOCATION_START", tool_name, params_sent)
    logger.info(f"[{tool_name}] Attempting to get flight status for booking {booking_id}")
    
    try:
        result = travel_mock_data.get_flight_status(booking_id)
        logger.info(f"[{tool_name}] Received from travel_mock_data.get_flight_status: {result}")
        
        if result.get("status") == "SUCCESS":
            api_response = {
                "status": "success",
                "flight_status": result.get("flight_status"),
                "message": "Flight status retrieved successfully"
            }
        else:
            api_response = {
                "status": "error",
                "message": result.get("message", "Failed to retrieve flight status")
            }
    except Exception as e:
        logger.error(f"[{tool_name}] Error calling travel_mock_data.get_flight_status: {e}", exc_info=True)
        api_response = {"status": "error", "message": "An internal error occurred while retrieving flight status"}
    
    _log_tool_event("INVOCATION_END", tool_name, params_sent, api_response)
    return api_response

async def searchHotels(city: str, check_in_date: str, check_out_date: str, guests: int = 1):
    tool_name = "searchHotels"
    params_sent = {"city": city, "check_in_date": check_in_date, "check_out_date": check_out_date, "guests": guests}
    _log_tool_event("INVOCATION_START", tool_name, params_sent)
    logger.info(f"[{tool_name}] Attempting to search hotels in {city} from {check_in_date} to {check_out_date}")
    
    try:
        result = travel_mock_data.search_hotels(city, check_in_date, check_out_date, guests)
        logger.info(f"[{tool_name}] Received from travel_mock_data.search_hotels: {result}")
        
        if result.get("status") == "SUCCESS":
            api_response = {
                "status": "success",
                "hotels": result.get("hotels", []),
                "message": f"Found {len(result.get('hotels', []))} hotels in {city}"
            }
        elif result.get("status") == "NO_HOTELS_FOUND":
            api_response = {
                "status": "no_results",
                "message": result.get("message", f"No hotels found in {city}"),
                "hotels": []
            }
        else:
            api_response = {
                "status": "error",
                "message": result.get("message", "Failed to search hotels")
            }
    except Exception as e:
        logger.error(f"[{tool_name}] Error calling travel_mock_data.search_hotels: {e}", exc_info=True)
        api_response = {"status": "error", "message": "An internal error occurred while searching hotels"}
    
    _log_tool_event("INVOCATION_END", tool_name, params_sent, api_response)
    return api_response

async def bookHotel(hotel_id: str, guest_name: str, guest_email: str, check_in_date: str, check_out_date: str, rooms: int = 1):
    tool_name = "bookHotel"
    params_sent = {"hotel_id": hotel_id, "guest_name": guest_name, "guest_email": guest_email, 
                   "check_in_date": check_in_date, "check_out_date": check_out_date, "rooms": rooms}
    _log_tool_event("INVOCATION_START", tool_name, params_sent)
    logger.info(f"[{tool_name}] Attempting to book hotel {hotel_id} for {guest_name}")
    
    try:
        result = travel_mock_data.book_hotel(hotel_id, guest_name, guest_email, check_in_date, check_out_date, rooms)
        logger.info(f"[{tool_name}] Received from travel_mock_data.book_hotel: {result}")
        
        if result.get("status") == "SUCCESS":
            api_response = {
                "status": "success",
                "message": result.get("message"),
                "booking_id": result.get("booking_id"),
                "total_cost": result.get("total_cost"),
                "currency": result.get("currency"),
                "nights": result.get("nights")
            }
        else:
            api_response = {
                "status": "error",
                "message": result.get("message", "Failed to book hotel")
            }
    except Exception as e:
        logger.error(f"[{tool_name}] Error calling travel_mock_data.book_hotel: {e}", exc_info=True)
        api_response = {"status": "error", "message": "An internal error occurred while booking the hotel"}
    
    _log_tool_event("INVOCATION_END", tool_name, params_sent, api_response)
    return api_response

async def getBookingDetails(booking_id: str):
    tool_name = "getBookingDetails"
    params_sent = {"booking_id": booking_id}
    _log_tool_event("INVOCATION_START", tool_name, params_sent)
    logger.info(f"[{tool_name}] Attempting to get booking details for {booking_id}")
    
    try:
        result = travel_mock_data.get_booking_details(booking_id)
        logger.info(f"[{tool_name}] Received from travel_mock_data.get_booking_details: {result}")
        
        if result.get("status") == "SUCCESS":
            api_response = {
                "status": "success",
                "booking": result.get("booking"),
                "message": "Booking details retrieved successfully"
            }
        else:
            api_response = {
                "status": "error",
                "message": result.get("message", "Failed to retrieve booking details")
            }
    except Exception as e:
        logger.error(f"[{tool_name}] Error calling travel_mock_data.get_booking_details: {e}", exc_info=True)
        api_response = {"status": "error", "message": "An internal error occurred while retrieving booking details"}
    
    _log_tool_event("INVOCATION_END", tool_name, params_sent, api_response)
    return api_response

async def listUserBookings():
    tool_name = "listUserBookings"
    params_sent = {}
    _log_tool_event("INVOCATION_START", tool_name, params_sent)
    logger.info(f"[{tool_name}] Attempting to list all bookings for user {USER_ID}")
    
    try:
        result = travel_mock_data.list_user_bookings(USER_ID)
        logger.info(f"[{tool_name}] Received from travel_mock_data.list_user_bookings: {result}")
        
        if result.get("status") == "SUCCESS":
            api_response = {
                "status": "success",
                "bookings": result.get("bookings", []),
                "message": f"Found {len(result.get('bookings', []))} booking(s)"
            }
        elif result.get("status") == "NO_BOOKINGS_FOUND":
            api_response = {
                "status": "success",
                "bookings": [],
                "message": result.get("message", "No bookings found")
            }
        else:
            api_response = {
                "status": "error",
                "message": result.get("message", "Failed to retrieve bookings")
            }
    except Exception as e:
        logger.error(f"[{tool_name}] Error calling travel_mock_data.list_user_bookings: {e}", exc_info=True)
        api_response = {"status": "error", "message": "An internal error occurred while retrieving bookings"}
    
    _log_tool_event("INVOCATION_END", tool_name, params_sent, api_response)
    return api_response

async def cancelBooking(booking_id: str):
    tool_name = "cancelBooking"
    params_sent = {"booking_id": booking_id}
    _log_tool_event("INVOCATION_START", tool_name, params_sent)
    logger.info(f"[{tool_name}] Attempting to cancel booking {booking_id}")
    
    try:
        result = travel_mock_data.cancel_booking(booking_id)
        logger.info(f"[{tool_name}] Received from travel_mock_data.cancel_booking: {result}")
        
        if result.get("status") == "SUCCESS":
            api_response = {
                "status": "success",
                "message": result.get("message", "Booking cancelled successfully")
            }
        else:
            api_response = {
                "status": "error",
                "message": result.get("message", "Failed to cancel booking")
            }
    except Exception as e:
        logger.error(f"[{tool_name}] Error calling travel_mock_data.cancel_booking: {e}", exc_info=True)
        api_response = {"status": "error", "message": "An internal error occurred while cancelling the booking"}
    
    _log_tool_event("INVOCATION_END", tool_name, params_sent, api_response)
    return api_response

async def getDestinationInfo(city: str):
    tool_name = "getDestinationInfo"
    params_sent = {"city": city}
    _log_tool_event("INVOCATION_START", tool_name, params_sent)
    logger.info(f"[{tool_name}] Attempting to get destination info for {city}")
    
    try:
        result = travel_mock_data.get_destination_info(city)
        logger.info(f"[{tool_name}] Received from travel_mock_data.get_destination_info: {result}")
        
        if result.get("status") == "SUCCESS":
            api_response = {
                "status": "success",
                "destination": result.get("destination"),
                "message": f"Destination information retrieved for {city}"
            }
        else:
            api_response = {
                "status": "error",
                "message": result.get("message", f"No information found for {city}")
            }
    except Exception as e:
        logger.error(f"[{tool_name}] Error calling travel_mock_data.get_destination_info: {e}", exc_info=True)
        api_response = {"status": "error", "message": "An internal error occurred while retrieving destination information"}
    
    _log_tool_event("INVOCATION_END", tool_name, params_sent, api_response)
    return api_response

async def getWeatherInfo(city: str):
    tool_name = "getWeatherInfo"
    params_sent = {"city": city}
    _log_tool_event("INVOCATION_START", tool_name, params_sent)
    logger.info(f"[{tool_name}] Attempting to get weather info for {city}")
    
    try:
        result = travel_mock_data.get_weather_info(city)
        logger.info(f"[{tool_name}] Received from travel_mock_data.get_weather_info: {result}")
        
        if result.get("status") == "SUCCESS":
            api_response = {
                "status": "success",
                "weather": result.get("weather"),
                "message": f"Weather information retrieved for {city}"
            }
        else:
            api_response = {
                "status": "error",
                "message": result.get("message", f"No weather information found for {city}")
            }
    except Exception as e:
        logger.error(f"[{tool_name}] Error calling travel_mock_data.get_weather_info: {e}", exc_info=True)
        api_response = {"status": "error", "message": "An internal error occurred while retrieving weather information"}
    
    _log_tool_event("INVOCATION_END", tool_name, params_sent, api_response)
    return api_response

async def searchActivities(city: str, activity_type: str = None):
    tool_name = "searchActivities"
    params_sent = {"city": city, "activity_type": activity_type}
    _log_tool_event("INVOCATION_START", tool_name, params_sent)
    logger.info(f"[{tool_name}] Attempting to search activities in {city}")
    
    try:
        result = travel_mock_data.search_activities(city, activity_type)
        logger.info(f"[{tool_name}] Received from travel_mock_data.search_activities: {result}")
        
        if result.get("status") == "SUCCESS":
            api_response = {
                "status": "success",
                "activities": result.get("activities", []),
                "message": f"Found {len(result.get('activities', []))} activities in {city}"
            }
        elif result.get("status") == "NO_ACTIVITIES_FOUND":
            api_response = {
                "status": "no_results",
                "message": result.get("message", f"No activities found in {city}"),
                "activities": []
            }
        else:
            api_response = {
                "status": "error",
                "message": result.get("message", "Failed to search activities")
            }
    except Exception as e:
        logger.error(f"[{tool_name}] Error calling travel_mock_data.search_activities: {e}", exc_info=True)
        api_response = {"status": "error", "message": "An internal error occurred while searching activities"}
    
    _log_tool_event("INVOCATION_END", tool_name, params_sent, api_response)
    return api_response

# Tool instance containing all travel function declarations
travel_tool = types.Tool(
    function_declarations=[
        searchFlights_declaration,
        bookFlight_declaration,
        getFlightStatus_declaration,
        searchHotels_declaration,
        bookHotel_declaration,
        getBookingDetails_declaration,
        listUserBookings_declaration,
        cancelBooking_declaration,
        getDestinationInfo_declaration,
        getWeatherInfo_declaration,
        searchActivities_declaration,
    ]
)