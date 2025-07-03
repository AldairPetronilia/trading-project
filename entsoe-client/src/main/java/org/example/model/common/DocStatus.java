package org.example.model.common;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.Arrays;

@Getter
@AllArgsConstructor
public enum DocStatus {
    INTERMEDIATE("A01", "Intermediate"),
    FINAL("A02", "Final"),
    ACTIVE("A05", "Active"),
    CANCELLED("A09", "Cancelled"),
    WITHDRAWN("A13", "Withdrawn"),
    ESTIMATED("X01", "Estimated");

    private final String code;
    private final String description;

    public static DocStatus fromCode(String code) {
        return Arrays.stream(values())
                .filter(type -> type.code.equals(code))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unknown DocStatus code: " + code));
    }
}
