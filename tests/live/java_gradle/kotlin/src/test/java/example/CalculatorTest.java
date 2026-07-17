package example;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

final class CalculatorTest {
  @Test
  void classifiesNegativeZeroAndPositiveValues() {
    assertEquals(-1, Calculator.classify(-1));
    assertEquals(0, Calculator.classify(0));
    assertEquals(1, Calculator.classify(1));
  }
}
