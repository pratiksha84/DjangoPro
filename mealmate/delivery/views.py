from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.conf import settings
import razorpay
from .models import Customer, Restaurant, Item, Cart

# Create your views here.
def say_hello(request):
    # return HttpResponse('Hello World')
    return render(request, 'index.html')

def open_signup(request):
    return render(request, 'signup.html')

def open_signin(request):
    return render(request, 'signin.html')

def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if Customer.objects.filter(username=username).exists():
            return HttpResponse('Duplicate username')

        Customer.objects.create(
            username=username,
            email=email,
            password=password,
        )
        return HttpResponse('Signup successful')

    return render(request, 'signup.html')

def signin(request):
    message = ''
    username = ''

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            customer = Customer.objects.get(username=username)
            if customer.password != password:
                message = 'Password invalid'
            else:
                if username == 'admin':
                    return render(request, 'admin_home.html')
                restaurantList = Restaurant.objects.all()
                return render(request, 'customer_home.html', {"restaurantList": restaurantList, "username": username})
        except Customer.DoesNotExist:
            message = 'Username invalid'

    return render(request, 'signin.html', {'message': message, 'username': username})


def open_add_restaurant(request):
    return render(request, 'add_restaurant.html')

def add_restaurant(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        picture = request.POST.get('picture')
        cuisine = request.POST.get('cuisine')
        rating = request.POST.get('rating')
        
        try:
            Restaurant.objects.get(name = name)
            return HttpResponse("Duplicate restaurant!")
        except:
            Restaurant.objects.create(
                name = name,
                picture = picture,
                cuisine = cuisine,
                rating = rating,
            )
    return render(request, 'admin_home.html')

def open_show_restaurant(request):
    restaurantList = Restaurant.objects.all()
    return render(request, 'show_restaurants.html', {"restaurantList": restaurantList})

def open_update_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id=restaurant_id)
    return render(request, 'update_restaurant.html', {"restaurant": restaurant})

def update_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        picture = request.POST.get('picture')
        cuisine = request.POST.get('cuisine')
        rating = request.POST.get('rating')
        
        restaurant.name = name
        restaurant.picture = picture
        restaurant.cuisine = cuisine
        restaurant.rating = rating

        restaurant.save()

    restaurantList = Restaurant.objects.all()
    return render(request, 'show_restaurants.html',{"restaurantList" : restaurantList})

def delete_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    restaurant.delete()

    restaurantList = Restaurant.objects.all()
    return render(request, 'show_restaurants.html',{"restaurantList" : restaurantList})


def open_update_menu(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    itemList = restaurant.items.all()
    #itemList = Item.objects.all()
    return render(request, 'update_menu.html',{"itemList" : itemList, "restaurant" : restaurant})
    
def update_menu(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        vegeterian = request.POST.get('vegeterian') == 'on'
        picture = request.POST.get('picture')
        
        if Item.objects.filter(restaurant=restaurant, name=name).exists():
            return HttpResponse("Duplicate item!")

        Item.objects.create(
            restaurant = restaurant,
            name = name,
            description = description,
            price = price,
            vegeterian = vegeterian,
            picture = picture,
        )

    return redirect('open_update_menu', restaurant_id=restaurant_id)


def delete_menu_item(request, restaurant_id, item_id):
    item = get_object_or_404(Item, id=item_id, restaurant_id=restaurant_id)
    item.delete()
    return redirect('open_update_menu', restaurant_id=restaurant_id)


def view_menu(request, restaurant_id, username):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    itemList = restaurant.items.all()
    # itemList = Item.objects.all()
    return render(request, 'customer_menu.html', {"itemList" : itemList, "restaurant" : restaurant, "username":username})

def add_to_cart(request, restaurant_id, item_id, username):
    item = Item.objects.get(id = item_id)
    customer = Customer.objects.get(username = username)

    cart, created = Cart.objects.get_or_create(customer = customer)
    cart.items.add(item)

    return redirect('view_menu', restaurant_id=restaurant_id, username=username)


def remove_from_cart(request, item_id, username):
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    if cart:
        item = get_object_or_404(Item, id=item_id)
        cart.items.remove(item)
    return redirect('show_cart', username=username)


def show_cart(request, username):
    customer = Customer.objects.get(username = username)
    cart = Cart.objects.filter(customer=customer).first()
    items = cart.items.all() if cart else []
    total_price = cart.total_price() if cart else 0

    return render(request, 'cart.html',{"itemList" : items, "total_price" : total_price, "username":username})

def checkout(request, username):
    # Fetch customer and their cart
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    cart_items = cart.items.all() if cart else []
    total_price = cart.total_price() if cart else 0

    if total_price == 0:
        return render(request, 'checkout.html', {
            'error': 'Your cart is empty!',
        })
        
    # Initialize Razorpay client
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    # Avoid failing through system proxy env vars in local dev.
    client.session.trust_env = False
    
    # create a Razorpay order
    order_date = {
        'amount': int(total_price * 100),  # Razorpay expects amount in paise
        'currency': 'INR',
        'payment_capture': '1'  # Auto-capture payment
    }
    try:
        order = client.order.create(data=order_date)
    except Exception as e:
        return render(request, 'checkout.html', {
            'username': username,
            'cart_items': cart_items,
            'total_price': total_price,
            'error': f'Payment service is currently unavailable. Please try again later.',
        })

    # Pass the order details to the frontend
    return render(request, 'checkout.html', {
        'username': username,
        'cart_items': cart_items,
        'total_price': total_price,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'order_id': order['id'],
        'amount_paise': order_date['amount'],
    })


# Orders Page
def orders(request, username):
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()

    # Fetch cart items and total price before clearing the cart
    cart_items = cart.items.all() if cart else []
    total_price = cart.total_price() if cart else 0

    # Clear the cart after fetching its details
    if cart:
        cart.items.clear()

    return render(request, 'orders.html', {
        'username': username,
        'customer': customer,
        'cart_items': cart_items,
        'total_price': total_price,
    })

