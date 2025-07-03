package org.example.model.common;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.Arrays;

@Getter
@AllArgsConstructor
public enum CurveType {
    SEQUENTIAL_FIXED_SIZE_BLOCK("A01", "Sequential fixed size block"),
    POINT_TO_POINT("A02", "Point to point"),
    VARIABLE_SIZED_BLOCK("A03", "Variable sized block");

    private final String code;
    private final String description;

    public static CurveType fromCode(String code) {
        return Arrays.stream(values())
                .filter(type -> type.code.equals(code))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unknown CurveType code: " + code));
    }
}
