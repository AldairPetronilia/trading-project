package com.example.energydataservice.model;

/**
 * Process types as defined in the ENTSO-E API documentation
 */
public enum ProcessType {
    A01("Day ahead"),
    A02("Intra day incremental"),
    A16("Realised"),
    A18("Intraday total"),
    A31("Week ahead"),
    A32("Month ahead"),
    A33("Year ahead"),
    A39("Synchronisation process"),
    A40("Intraday process"),
    A46("Replacement reserve"),
    A47("Manual frequency restoration reserve"),
    A51("Automatic frequency restoration reserve"),
    A52("Frequency containment reserve"),
    A56("Frequency restoration reserve"),
    A60("Scheduled activation mFRR"),
    A61("Direct activation mFRR"),
    A67("Central Selection aFRR"),
    A68("Local Selection aFRR");

    private final String description;

    ProcessType(String description) {
        this.description = description;
    }

    public String getDescription() {
        return description;
    }
}
