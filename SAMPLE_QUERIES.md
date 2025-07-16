# Travel Assistant Sample Queries

This document contains comprehensive test queries for the travel assistant voice interface. Use these queries to test the functionality of flight searches, hotel bookings, destination information, and other travel-related features.

## 🛫 Flight Search & Booking

### Basic Flight Searches

**Query 1: Simple Flight Search**
```
"Search for flights from Mumbai to Dubai on February 15th, 2024"
```
*Expected: Returns Emirates flight EK234 with details*

**Query 2: Alternative Search Variations**
```
"Find flights from BOM to DXB on 2024-02-15"
"I need to fly from Mumbai to Dubai on February 15th"
"Show me available flights Mumbai to Dubai February 15"
```

**Query 3: Domestic Flight Search**
```
"Search for flights from Delhi to Mumbai on February 16th, 2024"
```
*Expected: Returns Air India flight AI131*

**Query 4: Multiple Passengers**
```
"Find flights from Mumbai to Dubai on February 15th for 2 passengers"
```
*Expected: Should check seat availability for multiple passengers*

### Flight Booking

**Query 5: Book a Flight**
```
"Book flight FL001 for John Doe with email john@example.com"
```
*Expected: Creates booking and returns booking ID*

**Query 6: Book with Multiple Passengers**
```
"Book flight FL002 for 2 passengers, name is Jane Smith, email jane@example.com"
```

### Flight Status

**Query 7: Check Flight Status**
```
"What's the status of my booking BK12345678?"
"Check flight status for booking reference BK12345678"
```
*Expected: Returns flight status, gate, terminal info*

---

## 🏨 Hotel Search & Booking

### Hotel Searches

**Query 8: Basic Hotel Search**
```
"Search for hotels in Dubai from February 15th to February 17th"
"Find hotels in Dubai check-in February 15, check-out February 17"
```
*Expected: Returns Burj Al Arab hotel*

**Query 9: Alternative Cities**
```
"Search for hotels in Mumbai from February 20th to February 22nd"
"Find accommodation in Goa from March 1st to March 3rd"
"Look for hotels in Bangalore for March 5th to March 7th"
```

**Query 10: Multiple Guests**
```
"Search for hotels in Dubai from February 15th to February 17th for 2 guests"
```

### Hotel Booking

**Query 11: Book a Hotel**
```
"Book hotel HTL004 for John Smith, email john.smith@email.com, check-in February 15th, check-out February 17th"
```
*Expected: Creates hotel booking with cost calculation*

**Query 12: Multiple Rooms**
```
"Book hotel HTL001 for 2 rooms, guest name Mary Johnson, email mary@email.com, check-in February 20th, check-out February 22nd"
```

---

## 📋 Booking Management

### View Bookings

**Query 13: List All Bookings**
```
"Show me all my bookings"
"What bookings do I have?"
"List my travel reservations"
```
*Expected: Returns all user bookings (flights and hotels)*

**Query 14: Get Specific Booking Details**
```
"Show me details for booking BK12345678"
"What are the details of my booking reference BK87654321?"
```

### Cancel Bookings

**Query 15: Cancel a Booking**
```
"Cancel my booking BK12345678"
"I want to cancel booking reference BK87654321"
```
*Expected: Cancels booking and restores availability*

---

## 🌍 Travel Information

### Destination Information

**Query 16: Destination Guide**
```
"Tell me about Dubai"
"What can you tell me about Goa as a travel destination?"
"Give me information about Dubai attractions"
```
*Expected: Returns description, attractions, best time to visit*

**Query 17: Specific Destination Queries**
```
"What are the popular attractions in Dubai?"
"When is the best time to visit Goa?"
"What language do they speak in Dubai?"
```

### Weather Information

**Query 18: Current Weather**
```
"What's the weather like in Dubai?"
"Tell me the weather forecast for Goa"
"Is it sunny in Dubai right now?"
```
*Expected: Returns current weather and 3-day forecast*

**Query 19: Weather for Travel Planning**
```
"Should I pack warm clothes for Dubai in February?"
"What's the weather going to be like in Goa next week?"
```

### Activities & Attractions

**Query 20: Search Activities**
```
"What activities are available in Dubai?"
"Find things to do in Goa"
"Show me sightseeing options in Dubai"
```
*Expected: Returns available activities with prices*

**Query 21: Specific Activity Types**
```
"Find adventure activities in Goa"
"What sightseeing activities are there in Dubai?"
"Show me cultural activities in Mumbai"
```

---

## 🔄 Complex Scenarios & Workflows

### Multi-Step Booking Process

**Query 22: Complete Travel Planning**
```
1. "Search for flights from Mumbai to Dubai on February 15th"
2. "Book flight FL001 for John Doe, email john@example.com"
3. "Now search for hotels in Dubai from February 15th to February 17th"
4. "Book hotel HTL004 for John Doe, same email, check-in February 15th, check-out February 17th"
5. "Show me all my bookings"
```

### Travel Research Workflow

**Query 23: Trip Planning Sequence**
```
1. "Tell me about Dubai as a destination"
2. "What's the weather like in Dubai?"
3. "What activities are available in Dubai?"
4. "Search for flights from Mumbai to Dubai on February 15th"
5. "Search for hotels in Dubai from February 15th to February 17th"
```

---

## ❌ Error Scenarios & Edge Cases

### Invalid Searches

**Query 24: Non-Existent Routes**
```
"Search for flights from Mumbai to London on February 15th"
```
*Expected: Returns "No flights found" message*

**Query 25: Invalid Dates**
```
"Search for hotels in Dubai from February 30th to March 1st"
```

**Query 26: Invalid Cities**
```
"Search for hotels in Atlantis from February 15th to February 17th"
"Tell me about the weather in Narnia"
```

### Booking Errors

**Query 27: Invalid Flight ID**
```
"Book flight FL999 for John Doe, email john@example.com"
```
*Expected: Returns "Flight not found" error*

**Query 28: Invalid Booking Reference**
```
"Show me details for booking BK99999999"
"Cancel booking reference INVALID123"
```
*Expected: Returns "Booking not found" error*

**Query 29: Insufficient Availability**
```
"Book flight FL001 for 20 passengers, name John Doe, email john@example.com"
```
*Expected: Returns "Insufficient seats" error*

### Invalid Hotel Scenarios

**Query 30: Check-out Before Check-in**
```
"Search for hotels in Dubai from February 17th to February 15th"
```
*Expected: Returns date validation error*

**Query 31: Invalid Hotel ID**
```
"Book hotel HTL999 for John Doe, email john@example.com, check-in February 15th, check-out February 17th"
```

---

## 🗣️ Natural Language Variations

### Conversational Styles

**Query 32: Casual Conversational**
```
"Hey, I want to go to Dubai next month"
"Can you help me find a flight to Dubai?"
"I'm looking for a nice hotel in Mumbai"
"What's it like in Goa this time of year?"
```

**Query 33: Polite Formal**
```
"Could you please search for flights from Mumbai to Dubai?"
"I would like to book a hotel room in Dubai, please"
"May I see all my current bookings?"
```

**Query 34: Urgent/Quick**
```
"Quick, find me a flight to Dubai"
"I need a hotel in Mumbai tonight"
"Cancel my booking now"
```

### Different Date Formats

**Query 35: Various Date Expressions**
```
"Search flights for tomorrow"
"Find hotels for next week"
"Book for February 15th, 2024"
"I need accommodation for 2024-02-15"
"Hotels for Feb 15 to Feb 17"
"February fifteenth to February seventeenth"
```

---

## 📝 Testing Notes

### Success Indicators
- ✅ Function calls are made correctly
- ✅ Appropriate mock data is returned
- ✅ Error messages are clear and helpful
- ✅ Booking IDs are generated and can be referenced
- ✅ Availability is properly managed
- ✅ Logging shows successful operations

### Voice Interface Testing Tips
1. **Speak clearly** and at normal pace
2. **Use natural language** - the assistant handles conversational queries
3. **Be specific** with dates, names, and requirements
4. **Test interruptions** - try speaking while the assistant is responding
5. **Test noise scenarios** - background noise handling
6. **Multi-turn conversations** - building on previous queries

### Expected Response Times
- Flight/Hotel searches: 1-2 seconds
- Bookings: 1-2 seconds  
- Information queries: 1 second
- Error responses: Immediate

### Data Persistence Notes
- Bookings persist in memory during the session
- Availability updates when bookings are made
- Cancelled bookings restore availability
- All operations are logged for debugging

---

## 🚀 Advanced Testing Scenarios

### Stress Testing

**Query 36: Rapid Fire Requests**
```
Quickly ask multiple queries in succession:
1. "Search flights Mumbai to Dubai February 15th"
2. "Search hotels Dubai February 15th to 17th"  
3. "What's the weather in Dubai?"
4. "Show my bookings"
```

### Interruption Testing

**Query 37: Mid-Response Interruptions**
```
1. Start: "Tell me about all the attractions in Dubai..."
2. Interrupt while assistant is speaking: "Actually, show me flights instead"
```

### Context Switching

**Query 38: Topic Changes**
```
1. "Search for flights to Dubai"
2. "Actually, tell me about the weather first"
3. "Now back to those flights"
4. "What hotels are available there?"
```

---

## 📊 Performance Metrics to Monitor

- **Response Time**: < 2 seconds for most queries
- **Function Call Success Rate**: > 95%
- **Voice Recognition Accuracy**: Monitor transcription quality
- **Error Recovery**: Graceful handling of invalid inputs
- **Memory Usage**: Stable during extended sessions
- **Logging Completeness**: All operations properly logged

---

*Happy Testing! 🎉*

For technical support or to report issues, check the application logs or contact the development team.