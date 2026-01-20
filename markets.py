from flask import Blueprint, jsonify, request
from kalshi.api_client import get_kalshi_client

markets_bp = Blueprint('markets', __name__)

@markets_bp.route('/markets', methods=['GET'])
def get_markets():
    try:
        limit = int(request.args.get('limit', 100))
        cursor = request.args.get('cursor')
        client = get_kalshi_client()
        data = client.get_markets(limit=limit, cursor=cursor)
        markets = []
        for market in data.get('markets', []):
            try:
                orderbook = client.get_market_orderbook(market['ticker'])
                yes_orders = orderbook.get('orderbook', {}).get('yes', [])
                no_orders = orderbook.get('orderbook', {}).get('no', [])
                yes_bid = yes_orders[0]['price'] if yes_orders else 0
                yes_ask = yes_orders[-1]['price'] if yes_orders else 100
                no_bid = no_orders[0]['price'] if no_orders else 0
                no_ask = no_orders[-1]['price'] if no_orders else 100
                liquidity = sum(o.get('quantity', 0) for o in yes_orders[:5])
                liquidity += sum(o.get('quantity', 0) for o in no_orders[:5])
            except:
                yes_bid = 0
                yes_ask = 100
                no_bid = 0
                no_ask = 100
                liquidity = 0
                markets.append({
                'ticker': market['ticker'],
                'title': market.get('title', ''),
                'yes_bid': yes_bid,
                'yes_ask': yes_ask,
                'no_bid': no_bid,
                'no_ask': no_ask,
                'volume': market.get('volume', 0),
                'open_interest': market.get('open_interest', 0),
                'liquidity': liquidity,
                'close_time': market.get('close_time', ''),
                'category': market.get('category', 'Other'),
                'result': market.get('result')
            })
        return jsonify({'markets': markets, 'cursor': data.get('cursor')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@markets_bp.route('/markets/<ticker>', methods=['GET'])
def get_market_detail(ticker: str):
    try:
        client = get_kalshi_client()
        markets_data = client.get_markets(limit=1000)
        market = next((m for m in markets_data['markets'] if m['ticker'] == ticker), None)
        if not market:
            return jsonify({'error': 'Market not found'}), 404
        orderbook = client.get_market_orderbook(ticker)
        history = client.get_market_history(ticker, limit=100)
        return jsonify({'market': market, 'orderbook': orderbook, 'history': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
