package org.example.client;

import java.time.LocalDateTime;
import org.example.model.common.AreaCode;
import org.example.model.load.GLMarketDocument;

/**
 * Client interface for ENTSO-E Transparency Platform Load Domain API Provides access to load data
 * and forecasts according to ENTSO-E specifications
 */
public interface EntsoEClient extends AutoCloseable {

  /**
   * Retrieves actual total load data [6.1.A] Returns real-time load consumption data for a
   * specified bidding zone and time period. One year range limit applies, minimum time interval is
   * one MTU period.
   *
   * @param biddingZone The bidding zone to query (must be a valid BZN area type)
   * @param periodStart Start of the time period (inclusive)
   * @param periodEnd End of the time period (exclusive)
   * @param offset Optional pagination offset for large result sets (null for no offset)
   * @return Market document containing actual load data points
   * @throws EntsoEClientException if the request fails or parameters are invalid
   */
  GLMarketDocument getActualTotalLoad(
      AreaCode biddingZone, LocalDateTime periodStart, LocalDateTime periodEnd, Integer offset)
      throws EntsoEClientException;

  /**
   * Retrieves day-ahead total load forecast [6.1.B] Returns load forecasts published one day ahead
   * for planning purposes. One year range limit applies, minimum time interval is one day.
   *
   * @param biddingZone The bidding zone to query (must be a valid BZN area type)
   * @param periodStart Start of the time period (inclusive)
   * @param periodEnd End of the time period (exclusive)
   * @param offset Optional pagination offset for large result sets (null for no offset)
   * @return Market document containing day-ahead load forecast data
   * @throws EntsoEClientException if the request fails or parameters are invalid
   */
  GLMarketDocument getDayAheadLoadForecast(
      AreaCode biddingZone, LocalDateTime periodStart, LocalDateTime periodEnd, Integer offset)
      throws EntsoEClientException;

  /**
   * Retrieves week-ahead total load forecast [6.1.C] Returns load forecasts published one week
   * ahead for medium-term planning. One year range limit applies, minimum time interval is one
   * week.
   *
   * @param biddingZone The bidding zone to query (must be a valid BZN area type)
   * @param periodStart Start of the time period (inclusive)
   * @param periodEnd End of the time period (exclusive)
   * @param offset Optional pagination offset for large result sets (null for no offset)
   * @return Market document containing week-ahead load forecast data
   * @throws EntsoEClientException if the request fails or parameters are invalid
   */
  GLMarketDocument getWeekAheadLoadForecast(
      AreaCode biddingZone, LocalDateTime periodStart, LocalDateTime periodEnd, Integer offset)
      throws EntsoEClientException;

  /**
   * Retrieves month-ahead total load forecast [6.1.D] Returns load forecasts published one month
   * ahead for long-term planning. One year range limit applies, minimum time interval is one month.
   *
   * @param biddingZone The bidding zone to query (must be a valid BZN area type)
   * @param periodStart Start of the time period (inclusive)
   * @param periodEnd End of the time period (exclusive)
   * @param offset Optional pagination offset for large result sets (null for no offset)
   * @return Market document containing month-ahead load forecast data
   * @throws EntsoEClientException if the request fails or parameters are invalid
   */
  GLMarketDocument getMonthAheadLoadForecast(
      AreaCode biddingZone, LocalDateTime periodStart, LocalDateTime periodEnd, Integer offset)
      throws EntsoEClientException;

  /**
   * Retrieves year-ahead total load forecast [6.1.E] Returns load forecasts published one year
   * ahead for strategic planning. One year range limit applies, minimum time interval is one year.
   *
   * @param biddingZone The bidding zone to query (must be a valid BZN area type)
   * @param periodStart Start of the time period (inclusive)
   * @param periodEnd End of the time period (exclusive)
   * @param offset Optional pagination offset for large result sets (null for no offset)
   * @return Market document containing year-ahead load forecast data
   * @throws EntsoEClientException if the request fails or parameters are invalid
   */
  GLMarketDocument getYearAheadLoadForecast(
      AreaCode biddingZone, LocalDateTime periodStart, LocalDateTime periodEnd, Integer offset)
      throws EntsoEClientException;

  /**
   * Retrieves year-ahead forecast margin [8.1] Returns forecast margin data indicating the
   * uncertainty/confidence level of year-ahead load forecasts for capacity planning. One year range
   * limit applies, minimum time interval is one year.
   *
   * @param biddingZone The bidding zone to query (must be a valid BZN area type)
   * @param periodStart Start of the time period (inclusive)
   * @param periodEnd End of the time period (exclusive)
   * @param offset Optional pagination offset for large result sets (null for no offset)
   * @return Market document containing year-ahead forecast margin data
   * @throws EntsoEClientException if the request fails or parameters are invalid
   */
  GLMarketDocument getYearAheadForecastMargin(
      AreaCode biddingZone, LocalDateTime periodStart, LocalDateTime periodEnd, Integer offset)
      throws EntsoEClientException;

  /** Closes the client and releases any underlying resources */
  @Override
  void close();
}
