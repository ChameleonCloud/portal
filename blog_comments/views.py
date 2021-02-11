from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_list_or_404, get_object_or_404, redirect, render
from django.utils import html
from djangocms_blog.models import Post

from .forms import CommentForm


def add_comment_to_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.text = comment.text
            comment.save()
            next = request.POST.get("next", "/")
            messages.success(request, "Comment Added Successfully")
            return HttpResponseRedirect(next)
    else:
        form = CommentForm()
    return render(request, "djangocms_blog/add_comment_to_post.html", {"form": form})
