from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.db.models import Count
from django.utils import timezone
from django.conf import settings
from .models import Post, Category, Comment
from .forms import PostForm, CommentForm, CustomUserCreationForm, CustomUserChangeForm
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator

POSTS_PER_PAGE = 10

User = get_user_model()


def paginate_page(request, queryset, per_page=POSTS_PER_PAGE):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def get_queryset_with_comments():
    return Post.objects.select_related(
        'category', 'location', 'author'
    ).annotate(
        comment_count=Count('comments')
    )


def get_published_posts():
    return get_queryset_with_comments().filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now()
    )


class IndexListView(ListView):
    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'page_obj'
    
    def get_queryset(self):
        return get_published_posts().order_by('-pub_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_obj'] = paginate_page(self.request, self.get_queryset())
        return context


class CategoryPostsListView(ListView):
    model = Post
    template_name = 'blog/category.html'
    context_object_name = 'page_obj'
    
    def get_queryset(self):
        self.category = get_object_or_404(
            Category,
            slug=self.kwargs['category_slug'],
            is_published=True
        )

        return self.category.posts.filter(
            is_published=True,
            pub_date__lte=timezone.now()
        ).annotate(comment_count=Count('comments')).order_by('-pub_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['page_obj'] = paginate_page(self.request, self.get_queryset())
        return context


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'
    
    def get_object(self, queryset=None):
        post_id = self.kwargs.get(self.pk_url_kwarg)
        if self.request.user.is_authenticated:
            post = get_object_or_404(
                Post.objects.annotate(comment_count=Count('comments')),
                id=post_id
            )
            if post.author == self.request.user:
                return post
        return get_object_or_404(
            get_published_posts(),
            id=post_id
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = self.object.comments.select_related('author').order_by('created_at')
        context['form'] = CommentForm()
        return context 


class ProfileListView(ListView):
    model = Post
    template_name = 'blog/profile.html'
    context_object_name = 'page_obj'
    
    def get_queryset(self):
        self.profile_user = get_object_or_404(
            User,
            username=self.kwargs['username']
        )
        if self.request.user == self.profile_user:
            queryset = self.profile_user.posts.annotate(
                comment_count=Count('comments')
            ).order_by('-pub_date')
        else:
            queryset = self.profile_user.posts.filter(
                is_published=True,
                category__is_published=True,
                pub_date__lte=timezone.now()
            ).annotate(comment_count=Count('comments')).order_by('-pub_date')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.profile_user
        context['page_obj'] = paginate_page(self.request, self.get_queryset())
        return context


@login_required
def edit_profile(request):
    print("=== edit_profile view called ===")
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('blog:profile', username=request.user.username)
    else:
        form = CustomUserChangeForm(instance=request.user)
        print(f"Form class: {form.__class__}")
        print(f"Form is not None: {form is not None}")
    return render(request, 'blog/user.html', {'form': form})


def user_registration(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/registration_form.html', {'form': form})


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('blog:profile', kwargs={'username': self.request.user.username})


class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'  
    
    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return redirect('blog:post_detail', post_id=post.id)
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.id})

class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'  
    context_object_name = 'form'
    
    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return redirect('blog:post_detail', post_id=post.id)
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('blog:profile', kwargs={'username': self.request.user.username})

class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = get_object_or_404(Post, id=self.kwargs['post_id'])
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.kwargs['post_id']})


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'
    
    def dispatch(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.author != request.user:
            return redirect('blog:post_detail', post_id=comment.post.id)
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.post.id})


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'
    
    def dispatch(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.author != request.user:
            return redirect('blog:post_detail', post_id=comment.post.id)
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.post.id})
