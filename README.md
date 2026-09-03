🌟 Decora

Decora is a luxury home décor & furniture e-commerce platform built using Django. It provides a seamless shopping experience with advanced product & variant management, offers, coupons, wallet integration, Razorpay payments, referral rewards, and a full-featured admin dashboard.

🚀 Features

👤 User Features
- User Registration & Login (Email OTP verification)
- Google Authentication
- Profile Management
- Product Browsing (Category / Room based)
- Product Search & Filtering (price range, sort, category, room)
- Wishlist Management
- Shopping Cart
- Buy Now (quick single-item checkout)
- Secure Checkout with multiple payment methods (COD, Razorpay, Wallet)
- Razorpay Payment Retry on Failed Transactions
- Order Placement & Tracking
- Order History & Order Detail with Payment Status
- Item / Order Cancellation
- Product Return Requests
- Wallet System (refunds, cancellation credit, recharge via Razorpay)
- Product Reviews & Ratings
- Referral Rewards
- Coupon Application
- Downloadable PDF Invoices

🛠️ Admin Features
- Dashboard Analytics
- Product & Variant Combination Management
- Category & Room Management
- Inventory Management (stock tracking, low-stock alerts)
- Order Management (status transitions, payment status visibility)
- Return Request Approval / Rejection
- Coupon Management
- Offer Management (Category Offers)
- User Management
- Review Moderation (approve, hide, delete)

🏗️ Tech Stack

**Backend**
- Python
- Django

**Frontend**
- HTML5
- CSS3
- JavaScript
- Tailwind CSS

**Database**
- PostgreSQL

**Media Storage**
- Cloudinary

**Payments**
- Razorpay

**Authentication**
- Django Authentication
- Google OAuth

**PDF Generation**
- WeasyPrint (invoices)

📂 Project Structure
```
Decora/
│
├── apps/
│   ├── admin_side/
│   │   ├── catalog/
│   │   ├── coupons/
│   │   ├── customers/
│   │   ├── dashboard/
│   │   ├── inspiration/
│   │   ├── offers/
│   │   ├── orders/
│   │   └── sales/
│   │
│   ├── core/
│   │
│   └── user_side/
│       ├── accounts/
│       ├── cart/
│       ├── checkout/
│       ├── inspiration/
│       ├── orders/
│       ├── shop/
│       └── support/
│
├── media/
├── manage.py
├── requirements.txt
└── README.md
```

⚙️ Installation

**Clone Repository**
```bash
git clone https://github.com/raeesa7356-cyber/decora.git
cd decora
```

**Create Virtual Environment**
```bash
python -m venv venv
```

**Activate Virtual Environment**

Linux / Ubuntu:
```bash
source venv/bin/activate
```

Windows:
```bash
venv\Scripts\activate
```

**Install Dependencies**
```bash
pip install -r requirements.txt
```

**Apply Migrations**
```bash
python manage.py migrate
```

**Create Superuser**
```bash
python manage.py createsuperuser
```

**Run Development Server**
```bash
python manage.py runserver
```

Open: http://127.0.0.1:9200/

🎯 Core Modules

**Products**
- Product Listings
- Variant Combinations (color, material, etc.)
- Product Image Gallery
- Category & Room Association

**Cart & Checkout**
- Add to Cart
- Quantity Management
- Buy Now Flow
- Multi-step Checkout with Address Management
- Coupon Application at Checkout

**Orders**
- Order Placement
- Order Tracking (Pending → Shipped → Out for Delivery → Delivered)
- Order & Item Cancellation
- Return Requests & Admin Approval
- Payment Status (Paid / Pending / Failed / Refunded / Partially Refunded)
- Razorpay Payment Retry

**Offers & Coupons**
- Category Offers
- Coupon Discounts (percentage & fixed)
- Referral Benefits

**Wallet**
- Wallet Credits
- Refund Management (cancellation & return refunds)
- Wallet Recharge via Razorpay
- Referral Rewards

**Reviews**
- Product Ratings
- Customer Reviews
- Admin Moderation (approve / hide / delete)

🔒 Security Features
- CSRF Protection
- Authentication & Authorization
- Session Management
- Form Validation
- Stock Locking on Checkout (prevents overselling)

📈 Future Enhancements
- AI-Based Product Recommendations
- Advanced Sales Reports
- Email Notifications
- Mobile Application
- Multi-language Support

👨‍💻 Author

Raheesa Thesni

Built as a full-stack Django e-commerce project focused on luxury home décor & furniture retail.

📄 License

This project is intended for educational and portfolio purposes.
