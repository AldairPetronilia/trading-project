package com.example.energydataservice.model;

/**
 * Document status types
 */
public enum DocStatus {
    A01("Intermediate"),
    A02("Final"),
    A05("Active"),
    A09("Cancelled"),
    A13("Withdrawn"),
    X01("Estimated");

    private final String description;

    DocStatus(String description) {
        this.description = description;
    }

    public String getDescription() {
        return description;
    }
}
