from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from database import get_user_by_username, get_user_by_email, AccessLevel

class LoginForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    remember_me = BooleanField('تذكرني')
    submit = SubmitField('تسجيل الدخول')

class RegistrationForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    full_name = StringField('الاسم الكامل', validators=[DataRequired()])
    rank = StringField('الرتبة العسكرية')
    unit = StringField('الوحدة/القطعة')
    password = PasswordField('كلمة المرور', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('تسجيل')
    
    def validate_username(self, username):
        user = get_user_by_username(username.data)
        if user:
            raise ValidationError('اسم المستخدم مستخدم بالفعل. الرجاء اختيار اسم آخر.')
    
    def validate_email(self, email):
        user = get_user_by_email(email.data)
        if user:
            raise ValidationError('البريد الإلكتروني مستخدم بالفعل. الرجاء استخدام عنوان آخر.')

class UserProfileForm(FlaskForm):
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    full_name = StringField('الاسم الكامل', validators=[DataRequired()])
    rank = StringField('الرتبة العسكرية')
    unit = StringField('الوحدة/القطعة')
    current_password = PasswordField('كلمة المرور الحالية')
    new_password = PasswordField('كلمة المرور الجديدة', validators=[Length(min=8)])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[EqualTo('new_password')])
    submit = SubmitField('حفظ التغييرات')

class AdminUserForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    full_name = StringField('الاسم الكامل', validators=[DataRequired()])
    rank = StringField('الرتبة العسكرية')
    unit = StringField('الوحدة/القطعة')
    password = PasswordField('كلمة المرور', validators=[Length(min=8)])
    password2 = PasswordField('تأكيد كلمة المرور', validators=[EqualTo('password')])
    access_level = SelectField('مستوى الصلاحية', coerce=int)
    is_active = BooleanField('حساب نشط', default=True)
    submit = SubmitField('حفظ')
    
    def __init__(self, *args, **kwargs):
        super(AdminUserForm, self).__init__(*args, **kwargs)
        self.access_level.choices = [
            (AccessLevel.VISITOR.value, 'زائر'),
            (AccessLevel.ARCHIVIST.value, 'أمين أرشيف'),
            (AccessLevel.ANALYST.value, 'محلل'),
            (AccessLevel.COMMANDER.value, 'قائد'),
            (AccessLevel.ADMIN.value, 'مدير النظام')
        ]
    
    def validate_username(self, username):
        user_id = getattr(self, 'user_id', None)
        user = get_user_by_username(username.data)
        if user and (not user_id or user.id != user_id):
            raise ValidationError('اسم المستخدم مستخدم بالفعل. الرجاء اختيار اسم آخر.')
    
    def validate_email(self, email):
        user_id = getattr(self, 'user_id', None)
        user = get_user_by_email(email.data)
        if user and (not user_id or user.id != user_id):
            raise ValidationError('البريد الإلكتروني مستخدم بالفعل. الرجاء استخدام عنوان آخر.')
