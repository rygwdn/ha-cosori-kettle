# Makefile for C++ protocol tester
# This tests the envelope.h and protocol.cpp files against real device packets

CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -O2 -g -MMD -MP
INCLUDES = -I.

# Source files
SOURCES = test_cpp.cpp components/cosori_kettle_ble/protocol.cpp
OBJECTS = $(SOURCES:.cpp=.o)
DEPS = $(SOURCES:.cpp=.d)
TARGET = test_cpp

.PHONY: all clean test run compile

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(OBJECTS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

# Include dependency files
-include $(DEPS)

test: $(TARGET)
	./$(TARGET)

run: test compile

compile:
	uv run esphome compile cosori-kettle.build.yaml

clean:
	rm -f $(TARGET) $(OBJECTS) $(DEPS)
