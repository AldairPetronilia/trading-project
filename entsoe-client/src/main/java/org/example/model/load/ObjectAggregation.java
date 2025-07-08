package org.example.model.load;

import java.util.Arrays;
import lombok.AllArgsConstructor;
import lombok.Getter;

// Additional enum for Object Aggregation
@Getter
@AllArgsConstructor
public enum ObjectAggregation {
  AGGREGATED("A01", "Aggregated"),
  INDIVIDUAL("A02", "Individual");

  private final String code;
  private final String description;

  public static ObjectAggregation fromCode(String code) {
    return Arrays.stream(values())
        .filter(type -> type.code.equals(code))
        .findFirst()
        .orElseThrow(() -> new IllegalArgumentException("Unknown ObjectAggregation code: " + code));
  }
}
