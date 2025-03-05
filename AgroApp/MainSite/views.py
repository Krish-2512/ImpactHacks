from django.shortcuts import render
from .forms import  UserRegistrationForm, ProductForm
from .models import Product , Sale, Notification
from django.shortcuts import get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth import get_user_model


User = get_user_model()

# Create your views here.
def index(request):
    return render(request,'site.html')

def register(request):

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password1'])
                user.save()
                login(request, user)
                return redirect('profile')
            except IntegrityError:
                form.add_error('email', 'Use with this email Id already exists.')

    else:
        form = UserRegistrationForm()
    
    return render(request, 'register.html', {'form': form}) 


@login_required
def profile(request):
    return render(request, 'profile.html')    

@login_required
def dashboard(request):
    return render(request, 'dashboard/dashboard.html')


def user_list(request):
    users = User.objects.all()  # Fetch all registered users
    return render(request, 'customer/dashboard.html', {'users': users})

@login_required
def city(request):
    return render(request, 'dashboard/city.html')

@login_required
def sales(request):
    return render(request, 'dashboard/sales.html')

@login_required
def weather(request):
    return render(request, 'dashboard/weather.html')

@login_required
def notification(request):
    return render(request, 'dashboard/notification.html')    


@login_required
def product_list(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.user = request.user
            product.save()
            return JsonResponse({
                'success': True,
                'id': product.id,
                'name': product.name,
                'price': float(product.price),
                'quantity': product.quantity,
                'created_at': product.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    form = ProductForm()
    products = Product.objects.filter(user=request.user)
    return render(request, 'dashboard/product.html', {'form': form, 'products': products})


@login_required
def edit_product(request, product_id):
    """Handle editing an existing product."""
    product = get_object_or_404(Product, id=product_id, user=request.user)
    
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True,
                'id': product.id,
                'name': product.name,
                'price': float(product.price),
                'quantity': product.quantity,
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
def delete_product(request, product_id):
    """Handle deleting a product."""
    product = get_object_or_404(Product, id=product_id, user=request.user)
    
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        product.delete()
        return JsonResponse({'success': True, 'id': product_id})
    
    return JsonResponse({'success': False}, status=400)

@login_required
def sales_page(request):
    """Display all products and handle sales transactions."""
    products = Product.objects.filter(user=request.user)

    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        product_id = request.POST.get("product_id")
        quantity_sold = int(request.POST.get("quantity"))

        product = get_object_or_404(Product, id=product_id, user=request.user)

        if product.quantity >= quantity_sold:
            total_cost = product.price * quantity_sold
        
            product.quantity -= quantity_sold
            product.save()

            Sale.objects.create(product=product, quantity_sold=quantity_sold, total_cost=total_cost)

            return JsonResponse({
                "success": True,
                "product_id": product.id,
                "remaining_quantity": product.quantity,
                "total_cost": total_cost
            })
        else:
            return JsonResponse({"success": False, "error": "Not enough stock available"}, status=400)

    return render(request, "dashboard/sales.html", {"products": products})
User = get_user_model()  

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-timestamp')
    print(f"Fetched {len(notifications)} notifications for user: {request.user}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  
        return JsonResponse({"notifications": [
            {"id": n.id, "message": n.message, "timestamp": n.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
            for n in notifications
        ]})

    return render(request, 'dashboard/notification.html', {'notifications': notifications})

User = get_user_model()

# @login_required
def farmers_list(request):
    farmers = User.objects.all()  # Fetch all registered users
    return render(request, "customer/farmers_list.html", {"farmers": farmers})


def farmer_products(request, farmer_id):
    """Display products listed by a specific farmer."""
    farmer = get_object_or_404(User, id=farmer_id)
    products = Product.objects.filter(user=farmer)
    return render(request, "customer/farmer_products.html", {"farmer": farmer, "products": products})


@login_required
def purchase_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 0))

        if quantity <= 0:
            return JsonResponse({"success": False, "error": "Invalid quantity"}, status=400)

        if quantity > product.quantity:
            return JsonResponse({"success": False, "error": "Not enough stock available"}, status=400)

        # Calculate total cost
        total_cost = product.price * quantity

        # Deduct quantity from stock
        product.quantity -= quantity
        product.save()

        # Record the sale
        Sale.objects.create(product=product, quantity_sold=quantity, total_cost=total_cost)

        return JsonResponse({
            "success": True,
            "product_id": product.id,
            "remaining_quantity": product.quantity,
            "total_cost": float(total_cost),  # Convert Decimal to float for JSON response
        })

    return render(request, "customer/purchase_product.html", {"product": product})
@login_required
def delete_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    return JsonResponse({'success': True})



# @login_required
def purchase_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 0))

        if quantity <= 0:
            return render(request, "customer/purchase_product.html", {
                "product": product,
                "error": "Invalid quantity selected."
            })

        if quantity > product.quantity:
            return render(request, "customer/purchase_product.html", {
                "product": product,
                "error": "Not enough stock available."
            })

        # Calculate total cost
        total_cost = product.price * quantity

        # Deduct quantity from stock
        product.quantity -= quantity
        product.save()

        # Record the sale
        Sale.objects.create(product=product, quantity_sold=quantity, total_cost=total_cost)

        # Redirect to transactions page
        return redirect("transaction_history")

    return render(request, "customer/purchase_product.html", {"product": product})

def transaction_history(request):
    sales = Sale.objects.filter(product__user=request.user).order_by("-sold_at")
    purchases = Sale.objects.filter(product__in=Product.objects.filter(user=request.user)).order_by("-sold_at")

    return render(request, "customer/transaction_history.html", {"sales": sales, "purchases": purchases})

    return render(request, "customer/transaction_history.html", {"sales": sales})

@login_required
def generate_notifications():
    users = CustomUser.objects.all()
    for user in users:
        Notification.objects.create(user=user, message="This is an auto-generated notification!", timestamp=now())
    print("✅ Notifications created successfully!")