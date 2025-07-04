package org.example.api;

import lombok.Builder;
import lombok.Data;
import lombok.NonNull;
import org.example.model.common.*;

import java.time.LocalDateTime;

/**
 * Specialized builder for ENTSO-E Load Domain API endpoints
 * Supports all load-related data types with predefined configurations
 */
@Data
@Builder
public class LoadDomainRequestBuilder {

    @NonNull
    private AreaCode outBiddingZoneDomain;

    @NonNull
    private LocalDateTime periodStart;

    @NonNull
    private LocalDateTime periodEnd;

    // Optional parameters
    private String timeInterval;
    private Integer offset;

    // Fluent builder methods
    public LoadDomainRequestBuilder forBiddingZone(AreaCode biddingZone) {
        validateBiddingZone(biddingZone);
        this.outBiddingZoneDomain = biddingZone;
        return this;
    }

    public LoadDomainRequestBuilder fromPeriod(LocalDateTime start, LocalDateTime end) {
        validateDateRange(start, end);
        this.periodStart = start;
        this.periodEnd = end;
        return this;
    }

    public LoadDomainRequestBuilder withTimeInterval(String timeInterval) {
        this.timeInterval = timeInterval;
        return this;
    }

    public LoadDomainRequestBuilder withOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    /**
     * Builds EntsoEApiRequest for Actual Total Load [6.1.A]
     * DocumentType: A65 (System Total Load)
     * ProcessType: A16 (Realised)
     * One year range limit, minimum MTU period resolution
     */
    public EntsoEApiRequest buildActualTotalLoad() {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.SYSTEM_TOTAL_LOAD)      // A65
                .processType(ProcessType.REALISED)                 // A16
                .outBiddingZoneDomain(outBiddingZoneDomain)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build();
    }

    /**
     * Builds EntsoEApiRequest for Day-Ahead Total Load Forecast [6.1.B]
     * DocumentType: A65 (System Total Load)
     * ProcessType: A01 (Day Ahead)
     * One year range limit, minimum one day resolution
     */
    public EntsoEApiRequest buildDayAheadLoadForecast() {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.SYSTEM_TOTAL_LOAD)      // A65
                .processType(ProcessType.DAY_AHEAD)                // A01
                .outBiddingZoneDomain(outBiddingZoneDomain)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build();
    }

    /**
     * Builds EntsoEApiRequest for Week-Ahead Total Load Forecast [6.1.C]
     * DocumentType: A65 (System Total Load)
     * ProcessType: A31 (Week Ahead)
     * One year range limit, minimum one week resolution
     */
    public EntsoEApiRequest buildWeekAheadLoadForecast() {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.SYSTEM_TOTAL_LOAD)      // A65
                .processType(ProcessType.WEEK_AHEAD)               // A31
                .outBiddingZoneDomain(outBiddingZoneDomain)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build();
    }

    /**
     * Builds EntsoEApiRequest for Month-Ahead Total Load Forecast [6.1.D]
     * DocumentType: A65 (System Total Load)
     * ProcessType: A32 (Month Ahead)
     * One year range limit, minimum one month resolution
     */
    public EntsoEApiRequest buildMonthAheadLoadForecast() {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.SYSTEM_TOTAL_LOAD)      // A65
                .processType(ProcessType.MONTH_AHEAD)              // A32
                .outBiddingZoneDomain(outBiddingZoneDomain)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build();
    }

    /**
     * Builds EntsoEApiRequest for Year-Ahead Total Load Forecast [6.1.E]
     * DocumentType: A65 (System Total Load)
     * ProcessType: A33 (Year Ahead)
     * One year range limit, minimum one year resolution
     */
    public EntsoEApiRequest buildYearAheadLoadForecast() {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.SYSTEM_TOTAL_LOAD)      // A65
                .processType(ProcessType.YEAR_AHEAD)               // A33
                .outBiddingZoneDomain(outBiddingZoneDomain)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build();
    }

    /**
     * Builds EntsoEApiRequest for Year-Ahead Forecast Margin [8.1]
     * DocumentType: A70 (Load Forecast Margin)
     * ProcessType: A33 (Year Ahead)
     * One year range limit, minimum one year resolution
     */
    public EntsoEApiRequest buildYearAheadForecastMargin() {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.LOAD_FORECAST_MARGIN)   // A70
                .processType(ProcessType.YEAR_AHEAD)               // A33
                .outBiddingZoneDomain(outBiddingZoneDomain)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build();
    }

    // Validation methods
    private void validateBiddingZone(AreaCode areaCode) {
        if (areaCode != null && !areaCode.hasAreaType(AreaType.BZN)) {
            throw new IllegalArgumentException(
                    String.format("Area %s (%s) is not a valid bidding zone. Supported types: %s",
                            areaCode.getDescription(), areaCode.getCode(), areaCode.getAreaTypesList())
            );
        }
    }

    private void validateDateRange(LocalDateTime start, LocalDateTime end) {
        if (start != null && end != null) {
            if (start.isAfter(end)) {
                throw new IllegalArgumentException("Period start must be before period end");
            }

            // Check one year limit
            if (start.plusYears(1).isBefore(end)) {
                throw new IllegalArgumentException("Date range cannot exceed one year");
            }
        }
    }
}
