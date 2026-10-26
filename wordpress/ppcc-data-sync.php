<?php
/**
 * Country Check data sync (Code Snippets: run everywhere).
 * Pulls the approved master data file from the public repository on the server,
 * validates it, keeps the last good copy, and prints it into page 13392 only.
 * Visitors' browsers never contact GitHub. No credentials are stored.
 */
const PPCC_SOURCE = 'https://raw.githubusercontent.com/andrzej-dot/paragon-country-check-data/main/country-check-data.json'; // set at install
const PPCC_PAGE   = 13392;

function ppcc_valid( $d ) {
	if ( ! is_array( $d ) || ( $d['meta']['schema_version'] ?? 0 ) !== 1 ) return false;
	if ( count( $d['countries'] ?? array() ) < 200 ) return false;
	if ( count( $d['fto_listings'] ?? array() ) < 50 ) return false;
	foreach ( $d['countries'] as $c ) { if ( empty( $c['n'] ) ) return false; }
	return true;
}

function ppcc_fetch() {
	$r = wp_remote_get( PPCC_SOURCE . '?t=' . time(), array( 'timeout' => 20 ) );
	if ( is_wp_error( $r ) || wp_remote_retrieve_response_code( $r ) !== 200 ) { update_option( 'ppcc_last_error', 'fetch failed ' . gmdate( 'c' ), false ); return; }
	$body = wp_remote_retrieve_body( $r );
	$d    = json_decode( $body, true );
	if ( ! ppcc_valid( $d ) ) { update_option( 'ppcc_last_error', 'invalid data ' . gmdate( 'c' ), false ); return; }
	$hash = md5( $body );
	if ( get_option( 'ppcc_hash' ) === $hash ) { update_option( 'ppcc_checked', gmdate( 'c' ), false ); return; }
	update_option( 'ppcc_data_prev', get_option( 'ppcc_data' ), false );
	update_option( 'ppcc_data', $d, false );
	update_option( 'ppcc_hash', $hash, false );
	update_option( 'ppcc_checked', gmdate( 'c' ), false );
	delete_option( 'ppcc_last_error' );
	do_action( 'litespeed_purge_post', PPCC_PAGE );
}
add_action( 'ppcc_sync', 'ppcc_fetch' );
add_filter( 'cron_schedules', function ( $s ) { $s['ppcc_6h'] = array( 'interval' => 6 * HOUR_IN_SECONDS, 'display' => 'Every 6 hours' ); return $s; } );
add_action( 'init', function () {
	if ( ! wp_next_scheduled( 'ppcc_sync' ) ) wp_schedule_event( time() + 60, 'ppcc_6h', 'ppcc_sync' );
	if ( isset( $_GET['ppcc_refresh'] ) && current_user_can( 'manage_options' ) ) ppcc_fetch(); // manual refresh for admins
} );
add_action( 'wp_head', function () {
	if ( ! is_page( PPCC_PAGE ) ) return;
	$d = get_option( 'ppcc_data' );
	if ( ! $d ) return; // page falls back to "being updated"
	echo '<script id="ppcc-data">window.PPCC_DATA=' . wp_json_encode( $d ) . ';</script>' . "\n";
}, 1 );
