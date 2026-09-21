output "ec2_ip" {
  value       = aws_eip.api.public_ip
  description = "Elastic IP of the API instance."
}

output "cloudfront_url" {
  value       = "https://${aws_cloudfront_distribution.api.domain_name}"
  description = "HTTPS front door for the API (set as API_ORIGIN / ALLOWED_ORIGINS target)."
}

output "ssh_hint" {
  value = "ssh -i <private-key> ubuntu@${aws_eip.api.public_ip}"
}
