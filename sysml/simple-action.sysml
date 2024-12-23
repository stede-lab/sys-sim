package Sample {
  private import ScalarValues::*;

  action def doubleValue {
    in attribute a : Integer;
    out attribute b : Integer;
    if a < 99 {
      assign b := a * 2;
    } else {
      assign b := a;
    }
    terminate;
  }
}