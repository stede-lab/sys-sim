package Part_State_Demo {
  private import ScalarValues::*;

  state def LightState {

  }
  
  individual part def TrafficLight {
    attribute location : String;
    attribute inService : Boolean = false;
  }


}