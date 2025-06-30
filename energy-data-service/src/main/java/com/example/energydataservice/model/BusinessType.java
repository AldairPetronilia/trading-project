package com.example.energydataservice.model;

/**
 * Business types as defined in the ENTSO-E API documentation
 */
public enum BusinessType {
    A01("Production"),
    A04("Consumption"),
    A14("Aggregated energy data"),
    A19("Balance energy deviation"),
    A25("General Capacity Information"),
    A29("Already allocated capacity (AAC)"),
    A37("Installed generation"),
    A43("Requested capacity (without price)"),
    A46("System Operator redispatching"),
    A53("Planned maintenance"),
    A54("Unplanned outage"),
    A60("Minimum possible"),
    A61("Maximum possible"),
    A85("Internal redispatch"),
    A91("Positive forecast margin"),
    A92("Negative forecast margin"),
    A93("Wind generation"),
    A94("Solar generation"),
    A95("Frequency containment reserve"),
    A96("Automatic frequency restoration reserve"),
    A97("Manual frequency restoration reserve"),
    A98("Replacement reserve"),
    B01("Interconnector network evolution"),
    B02("Interconnector network dismantling"),
    B03("Counter trade"),
    B04("Congestion costs"),
    B05("Capacity allocated (including price)"),
    B07("Auction revenue"),
    B08("Total nominated capacity"),
    B09("Net position"),
    B10("Congestion income"),
    B11("Production unit"),
    B33("Area Control Error"),
    B74("Offer"),
    B75("Need"),
    B95("Procured capacity"),
    C22("Shared Balancing Reserve Capacity"),
    C23("Share of reserve capacity"),
    C24("Actual reserve capacity");

    private final String description;

    BusinessType(String description) {
        this.description = description;
    }

    public String getDescription() {
        return description;
    }
}
