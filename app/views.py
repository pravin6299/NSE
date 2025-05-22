from django.shortcuts import render
from django.db.models import Q
from .models import CorporateFiling, InstrumentDetails, HistoricalOHLC
from datetime import datetime
from django.core.paginator import Paginator
import pandas as pd
import numpy as np
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import now
# lalit
def index(request):
    # Get all filings ordered by filing date
    filings = CorporateFiling.objects.all().order_by('-filing_date')
    
    # Get search parameters
    company_name = request.GET.get('company_name', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    category = request.GET.get('category', '')
    
    # Apply filters if provided
    if company_name:
        filings = filings.filter(company_name__icontains=company_name)
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            filings = filings.filter(filing_date__gte=start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            filings = filings.filter(filing_date__lte=end_date)
        except ValueError:
            pass
    
    if category:
        filings = filings.filter(category=category)
    
    # Get distinct categories for dropdown
    category_values = CorporateFiling.objects.values_list('category', flat=True)
    # Use a set to ensure uniqueness, filter None values, and convert back to sorted list
    categories = sorted(set(c for c in category_values if c))
    
    context = {
        'filings': filings,
        'company_name': company_name,
        'start_date': start_date,
        'end_date': end_date,
        'selected_category': category,
        'categories': categories,
    }
    
    return render(request, 'app/index.html', context)


from django.shortcuts import render
from django.db.models import Q
from .models import InstrumentDetails, HistoricalOHLC

def instrument_list(request):
    # Get filter parameters
    search_query = request.GET.get('search', '')
    instrument_type = request.GET.get('instrument_type', '')
    segment = request.GET.get('segment', '')
    
    # Create a new queryset each time
    base_queryset = InstrumentDetails.objects.all()
    
    # Apply filters to the base queryset
    if search_query:
        base_queryset = base_queryset.filter(
            Q(tradingsymbol__icontains=search_query) |
            Q(name__icontains=search_query)
        )
    
    if instrument_type:
        base_queryset = base_queryset.filter(instrument_type=instrument_type)
    
    if segment:
        base_queryset = base_queryset.filter(segment=segment)
    
    # Get unique values for filters
    instrument_types = InstrumentDetails.objects.values_list('instrument_type', flat=True).distinct()
    segments = InstrumentDetails.objects.values_list('segment', flat=True).distinct()
    
    # Pagination
    paginator = Paginator(base_queryset, 25)  # Show 25 items per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'instrument_types': instrument_types,
        'segments': segments,
        'current_search': search_query,
        'current_instrument_type': instrument_type,
        'current_segment': segment,
    }
    
    return render(request, 'app/instrument_list.html', context)

def instrument_detail(request, instrument_id):
    try:
        instrument = InstrumentDetails.objects.get(id=instrument_id)
        # Get historical data for the last 30 days
        historical_data = HistoricalOHLC.objects.filter(
            instrument=instrument
        ).order_by('-timestamp')[:30]
        
        # Convert historical data to list of dictionaries for the chart
        historical_data_list = []
        for data in historical_data:
            historical_data_list.append({
                'timestamp': data.timestamp.strftime('%Y-%m-%d %H:%M'),
                'open': float(data.open),
                'high': float(data.high),
                'low': float(data.low),
                'close': float(data.close),
                'volume': int(data.volume),
                'interval': data.interval
            })
        
        context = {
            'instrument': instrument,
            'historical_data': historical_data,
            'historical_data_json': historical_data_list,  # For the chart
        }
        return render(request, 'app/instrument_detail.html', context)
    except InstrumentDetails.DoesNotExist:
        # Handle case where instrument is not found
        return render(request, 'app/error.html', {'message': 'Instrument not found'})

def process_stock_data(data_text):
    # Split the text into lines and remove empty lines
    lines = [line.strip() for line in data_text.strip().split('\n') if line.strip()]
    
    # Get headers from the first line
    headers = lines[0].split('\t')
    
    # Process data lines
    data = []
    for line in lines[1:]:
        values = line.split('\t')
        if len(values) == len(headers):
            # Create a dictionary with proper field names
            stock_data = {
                'Exc': values[0],
                'Segment': values[1],
                'name': values[2],
                'Exchange': values[3],
                'SECURITY_NAME': values[4],
                'SYMBOL': values[5],
                'LOT_SIZE': values[6],
                'price': float(values[7]) if values[7] else None,
                'priceopen': float(values[8]) if values[8] else None,
                'high': float(values[9]) if values[9] else None,
                'low': float(values[10]) if values[10] else None,
                'changepct': float(values[11]) if values[11] else None,
                'closeyest': float(values[12]) if values[12] else None,
                'Volume': int(values[13].replace(',', '')) if values[13] else None,
                'marketcap': float(values[14].replace(',', '')) if values[14] else None,
                'high52': float(values[15]) if values[15] else None,
                'low52': float(values[16]) if values[16] else None,
                'PRICE_CHANGE_5D': float(values[17]) if values[17] else None,
                'PRICE_CHANGE_10D': float(values[18]) if values[18] else None,
                'PRICE_CHANGE_20D': float(values[19]) if values[19] else None,
                'PRICE_CHANGE_30D': float(values[20]) if values[20] else None,
                'PRICE_CHANGE_60D': float(values[21]) if values[21] else None,
                'PRICE_CHANGE_90D': float(values[22]) if values[22] else None,
                'PRICE_CHANGE_6M': float(values[23]) if values[23] else None,
                'PRICE_CHANGE_1Y': float(values[24]) if values[24] else None,
                'PRICE_CHANGE_2Y': float(values[25]) if values[25] else None,
                'PRICE_CHANGE_3Y': float(values[26]) if values[26] else None,
                'PRICE_CHANGE_5Y': float(values[27]) if values[27] else None,
                'close': float(values[28]) if values[28] else None,
                'Outstanding_shares': int(values[29].replace(',', '')) if values[29] else None
            }
            data.append(stock_data)
    
    return pd.DataFrame(data)

import json
from django.core.paginator import Paginator
from django.shortcuts import render
from django.db.models import Q
from .models import InstrumentDetails

from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils.timezone import now
from datetime import timedelta
from .models import InstrumentDetails, HistoricalOHLC
import json

def get_change(stock_obj, latest_ohlc_obj, days):
    if not stock_obj or not latest_ohlc_obj:
        return None

    target_date = now().date() - timedelta(days=days)
    buffer_date = now().date() - timedelta(days=days + 2)

    past_ohlc = HistoricalOHLC.objects.filter(
        instrument=stock_obj,
        timestamp__date__lte=target_date,
        timestamp__date__gte=buffer_date,
        close__gt=0
    ).order_by('-timestamp').first()

    if past_ohlc and latest_ohlc_obj.close and past_ohlc.close:
        try:
            change = ((latest_ohlc_obj.close - past_ohlc.close) / past_ohlc.close) * 100
            return round(change, 2)
        except ZeroDivisionError:
            return None
    return None

from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q, Max, Min, Count
from django.utils.timezone import now
from collections import defaultdict
from datetime import timedelta

from .models import InstrumentDetails, HistoricalOHLC


from collections import defaultdict
from django.db.models import Q, Max, Min, Count
from django.shortcuts import render
from django.core.paginator import Paginator
from django.utils.timezone import now
from datetime import timedelta

from .models import InstrumentDetails, HistoricalOHLC


def calculate_price_change(stock, latest_ohlc, days):
    if not latest_ohlc:
        return None
    target_date = latest_ohlc.timestamp - timedelta(days=days)
    old_ohlc = HistoricalOHLC.objects.filter(
        instrument_id=stock.id,
        timestamp__lte=target_date
    ).order_by('-timestamp').first()
    if not old_ohlc or not old_ohlc.close:
        return None
    try:
        return round(((latest_ohlc.close - old_ohlc.close) / old_ohlc.close) * 100, 2)
    except ZeroDivisionError:
        return 0.0


def stock_market_view(request):
    search_query = request.GET.get('search', '')
    min_market_cap = request.GET.get('min_market_cap')
    max_market_cap = request.GET.get('max_market_cap')
    sort_by = request.GET.get('sort_by', '-instrument_token')
    segment = request.GET.get('segment', '')

    stocks = InstrumentDetails.objects.all()

    if search_query:
        stocks = stocks.filter(
            Q(tradingsymbol__icontains=search_query) |
            Q(name__icontains=search_query)
        )

    if segment:
        stocks = stocks.filter(segment=segment)

    if min_market_cap:
        try:
            stocks = stocks.filter(instrument_token__gte=float(min_market_cap))
        except ValueError:
            pass

    if max_market_cap:
        try:
            stocks = stocks.filter(instrument_token__lte=float(max_market_cap))
        except ValueError:
            pass

    if sort_by:
        stocks = stocks.order_by(sort_by)

    paginator = Paginator(stocks, 25)
    page_number = request.GET.get('page')
    current_page = paginator.get_page(page_number)
    current_ids = list(current_page.object_list.values_list('id', flat=True))

    # 52-week high and low
    one_year_ago = now() - timedelta(days=365)
    ohlc_agg = HistoricalOHLC.objects.filter(
        instrument_id__in=current_ids,
        timestamp__gte=one_year_ago
    ).values('instrument_id').annotate(
        high52=Max('high'),
        low52=Min('low')
    )
    high_low_map = {entry['instrument_id']: (entry['high52'], entry['low52']) for entry in ohlc_agg}

    # Count of historical rows
    historical_counts = HistoricalOHLC.objects.filter(
        instrument_id__in=current_ids
    ).values('instrument_id').annotate(count=Count('id'))
    historical_count_map = {entry['instrument_id']: entry['count'] for entry in historical_counts}

    latest_ohlcs = HistoricalOHLC.objects.filter(
        instrument_id__in=current_ids
    ).order_by('instrument_id', '-timestamp')

    ohlc_latest_map = {}
    ohlc_previous_map = defaultdict(list)
    for ohlc in latest_ohlcs:
        if ohlc.instrument_id not in ohlc_latest_map:
            ohlc_latest_map[ohlc.instrument_id] = ohlc
        elif len(ohlc_previous_map[ohlc.instrument_id]) < 1:
            ohlc_previous_map[ohlc.instrument_id].append(ohlc)

    stock_data_list = []
    for stock in current_page.object_list:
        latest_ohlc = ohlc_latest_map.get(stock.id)
        previous_ohlc = ohlc_previous_map.get(stock.id, [None])[0]

        current_price = latest_ohlc.close if latest_ohlc else 0.0
        previous_close = previous_ohlc.close if previous_ohlc else 0.0

        try:
            change_percent = ((current_price - previous_close) / previous_close) * 100 if previous_close else 0.0
        except ZeroDivisionError:
            change_percent = 0.0

        high52, low52 = high_low_map.get(stock.id, (0.0, 0.0))
        market_cap = current_price * getattr(stock, 'total_shares', 1)

        stock_data = {
            'tradingsymbol': stock.tradingsymbol,
            'name': stock.name,
            'segment': stock.segment,
            'change_percent': round(change_percent, 2),
            'price': round(current_price, 2),
            'open': latest_ohlc.open if latest_ohlc else None,
            'high': latest_ohlc.high if latest_ohlc else None,
            'low': latest_ohlc.low if latest_ohlc else None,
            'previous_close': previous_close,
            'volume': latest_ohlc.volume if latest_ohlc else None,
            'marketcap': round(market_cap, 2),
            'high52': round(high52 or 0.0, 2),
            'low52': round(low52 or 0.0, 2),
            'PRICE_CHANGE_5D': calculate_price_change(stock, latest_ohlc, 5),
            'PRICE_CHANGE_10D': calculate_price_change(stock, latest_ohlc, 10),
            'PRICE_CHANGE_20D': calculate_price_change(stock, latest_ohlc, 20),
            'PRICE_CHANGE_30D': calculate_price_change(stock, latest_ohlc, 30),
            'PRICE_CHANGE_60D': calculate_price_change(stock, latest_ohlc, 60),
            'PRICE_CHANGE_90D': calculate_price_change(stock, latest_ohlc, 90),
            'PRICE_CHANGE_6M': calculate_price_change(stock, latest_ohlc, 182),
            'PRICE_CHANGE_1Y': calculate_price_change(stock, latest_ohlc, 365),
            'PRICE_CHANGE_2Y': calculate_price_change(stock, latest_ohlc, 730),
            'PRICE_CHANGE_3Y': calculate_price_change(stock, latest_ohlc, 1095),
            'PRICE_CHANGE_5Y': calculate_price_change(stock, latest_ohlc, 1825),
            'historical_row_count': historical_count_map.get(stock.id, 0),
        }

        stock_data_list.append(stock_data)

    context = {
        'stock_data_list': stock_data_list,
        'period_keys': ['5D', '10D', '20D', '30D', '60D', '90D', '6M', '1Y', '2Y', '3Y', '5Y'],
        'page_obj': current_page,
        'current_search': search_query,
        'current_segment': segment,
        'current_min_market_cap': min_market_cap,
        'current_max_market_cap': max_market_cap,
        'current_sort': sort_by,
        'segments': InstrumentDetails.objects.values_list('segment', flat=True).distinct(),
        'stock_symbols': [s.tradingsymbol for s in current_page.object_list if s.tradingsymbol],
    }

    return render(request, 'app/stock_market.html', context)



def stock_detail_view(request, symbol):
    try:
        stock = InstrumentDetails.objects.filter(tradingsymbol=symbol).order_by('-timestamp').first()
        if not stock:
            return render(request, 'app/error.html', {'message': f'Stock with symbol {symbol} not found'})

        latest_ohlc = HistoricalOHLC.objects.filter(instrument=stock).order_by('-timestamp').first()

        def get_change(stock_obj, latest_ohlc_obj, days):
            if not stock_obj or not latest_ohlc_obj:
                return None

            target_date = now().date() - timedelta(days=days)
            buffer_date = now().date() - timedelta(days=days + 2)

            past_ohlc = HistoricalOHLC.objects.filter(
                instrument=stock_obj,
                timestamp__date__lte=target_date,
                timestamp__date__gte=buffer_date,
                close__gt=0
            ).order_by('-timestamp').first()

            if past_ohlc and latest_ohlc_obj.close and past_ohlc.close:
                try:
                    change = ((latest_ohlc_obj.close - past_ohlc.close) / past_ohlc.close) * 100
                    return round(change, 2)
                except ZeroDivisionError:
                    return None
            return None

        # 52W High & Low
        one_year_ago = now() - timedelta(days=365)
        high_52w = HistoricalOHLC.objects.filter(
            instrument=stock, timestamp__gte=one_year_ago
        ).order_by('-high').values_list('high', flat=True).first()

        low_52w = HistoricalOHLC.objects.filter(
            instrument=stock, timestamp__gte=one_year_ago
        ).order_by('low').values_list('low', flat=True).first()

        stock_data = {
            'SYMBOL': stock.tradingsymbol,
            'SECURITY_NAME': stock.name,
            'price': stock.last_price,
            'Volume': latest_ohlc.volume if latest_ohlc else stock.volume,
            'marketcap': stock.instrument_token,
            'high52': high_52w if high_52w is not None else 0.0,
            'low52': low_52w if low_52w is not None else 0.0,
            'Segment': stock.segment,
            'name': stock.instrument_type,
            'Exchange': stock.exchange,
            'LOT_SIZE': stock.lot_size,
            'changepct': get_change(stock, latest_ohlc, 1),
            'priceopen': latest_ohlc.open if latest_ohlc else None,
            'high': latest_ohlc.high if latest_ohlc else None,
            'low': latest_ohlc.low if latest_ohlc else None,
            'closeyest': latest_ohlc.close if latest_ohlc else None,

            # Historical percentage changes
            'PRICE_CHANGE_5D': get_change(stock, latest_ohlc, 5),
            'PRICE_CHANGE_10D': get_change(stock, latest_ohlc, 10),
            'PRICE_CHANGE_20D': get_change(stock, latest_ohlc, 20),
            'PRICE_CHANGE_30D': get_change(stock, latest_ohlc, 30),
            'PRICE_CHANGE_60D': get_change(stock, latest_ohlc, 60),
            'PRICE_CHANGE_90D': get_change(stock, latest_ohlc, 90),
            'PRICE_CHANGE_6M': get_change(stock, latest_ohlc, 180),
            'PRICE_CHANGE_1Y': get_change(stock, latest_ohlc, 365),
            'PRICE_CHANGE_2Y': get_change(stock, latest_ohlc, 730),
            'PRICE_CHANGE_3Y': get_change(stock, latest_ohlc, 1095),
            'PRICE_CHANGE_5Y': get_change(stock, latest_ohlc, 1825),
        }

        return render(request, 'app/stock_detail.html', {'stock': stock_data})

    except Exception as e:
        return render(request, 'app/error.html', {'message': str(e)})
