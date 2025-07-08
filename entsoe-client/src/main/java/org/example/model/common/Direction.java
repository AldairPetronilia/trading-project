package org.example.model.common;

import java.util.Arrays;
import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum Direction {
  UP("A01", "Up"),
  DOWN("A02", "Down"),
  SYMMETRIC("A03", "Symmetric");

  private final String code;
  private final String description;

  public static Direction fromCode(String code) {
    return Arrays.stream(values())
        .filter(type -> type.code.equals(code))
        .findFirst()
        .orElseThrow(() -> new IllegalArgumentException("Unknown Direction code: " + code));
  }
}
